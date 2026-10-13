from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chad.security.exfiltration import ExfiltrationGuard
from chad.security.prompt_injection import PromptInjectionDetector
from chad.security.sandbox_guard import SandboxEscapeGuard
from chad.security.threat_model import SecurityThreat, ThreatLevel, ThreatModelEvaluator
from chad.tools.permissions import PermissionEngine
from chad.tools.schema import ToolDefinition


@dataclass(frozen=True, slots=True)
class SecurityScanReport:
    is_allowed: bool
    threat_level: ThreatLevel
    threat_score: float
    threats: tuple[SecurityThreat, ...]
    sanitized_text: str | None = None
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_allowed": self.is_allowed,
            "threat_level": self.threat_level.value,
            "threat_score": self.threat_score,
            "threats": [t.to_dict() for t in self.threats],
            "sanitized_text": self.sanitized_text,
            "reasons": list(self.reasons),
        }


class SecurityEngine:
    """Unified security engine for CHAD providing threat modeling, prompt injection protection,
    exfiltration prevention, secret scanning, tool permission enforcement, and sandbox escape checks.
    """

    def __init__(
        self,
        injection_detector: PromptInjectionDetector | None = None,
        exfiltration_guard: ExfiltrationGuard | None = None,
        sandbox_guard: SandboxEscapeGuard | None = None,
        permission_engine: PermissionEngine | None = None,
        evaluator: ThreatModelEvaluator | None = None,
    ) -> None:
        self.injection_detector = injection_detector or PromptInjectionDetector()
        self.exfiltration_guard = exfiltration_guard or ExfiltrationGuard()
        self.sandbox_guard = sandbox_guard or SandboxEscapeGuard()
        self.permission_engine = permission_engine or PermissionEngine()
        self.evaluator = evaluator or ThreatModelEvaluator()

    def scan_input(self, text: str, source: str = "user_input") -> SecurityScanReport:
        """Scans user input or external input for prompt injection and malicious instructions."""
        inj_res = self.injection_detector.scan_text(text, source=source)
        threats: list[SecurityThreat] = []
        reasons: list[str] = []

        if inj_res.is_detected and inj_res.threat:
            threats.append(inj_res.threat)
            reasons.extend(inj_res.detected_patterns)

        threat_level, threat_score = self.evaluator.evaluate_threat_score(threats)
        is_allowed = threat_level not in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)

        return SecurityScanReport(
            is_allowed=is_allowed,
            threat_level=threat_level,
            threat_score=threat_score,
            threats=tuple(threats),
            sanitized_text=text,
            reasons=tuple(reasons),
        )

    def scan_output(self, text: str, source: str = "model_output") -> SecurityScanReport:
        """Scans assistant/model output for secret leakage, data exfiltration, or egress risks."""
        exfil_res = self.exfiltration_guard.scan_output(text, source=source)
        threats: list[SecurityThreat] = list(exfil_res.threats)
        reasons: list[str] = list(exfil_res.risk_reasons)

        threat_level, threat_score = self.evaluator.evaluate_threat_score(threats)
        is_allowed = threat_level != ThreatLevel.CRITICAL

        return SecurityScanReport(
            is_allowed=is_allowed,
            threat_level=threat_level,
            threat_score=threat_score,
            threats=tuple(threats),
            sanitized_text=exfil_res.sanitized_output,
            reasons=tuple(reasons),
        )

    def scan_sandbox_command(self, command: str) -> SecurityScanReport:
        """Scans code execution / shell commands for sandbox escape or system compromise attempts."""
        escape_res = self.sandbox_guard.scan_command(command)
        threats: list[SecurityThreat] = []
        reasons: list[str] = []

        if escape_res.is_escape_attempt and escape_res.threat:
            threats.append(escape_res.threat)
            reasons.extend(escape_res.reasons)

        threat_level, threat_score = self.evaluator.evaluate_threat_score(threats)
        is_allowed = threat_level not in (ThreatLevel.HIGH, ThreatLevel.CRITICAL)

        return SecurityScanReport(
            is_allowed=is_allowed,
            threat_level=threat_level,
            threat_score=threat_score,
            threats=tuple(threats),
            sanitized_text=command if is_allowed else "",
            reasons=tuple(reasons),
        )

    def check_tool_permission(
        self, tool: ToolDefinition, user_role: str = "user", has_user_approval: bool = False
    ) -> tuple[bool, str]:
        """Verifies if a tool call is authorized under current permission engine policy."""
        return self.permission_engine.is_permitted(tool, user_role=user_role, has_user_approval=has_user_approval)
