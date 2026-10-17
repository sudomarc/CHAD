from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from chad.agent.coder import SecretScanner
from chad.security.escape import SandboxEscapeGuard
from chad.security.exfiltration import ExfiltrationProtection
from chad.security.injection import PromptInjectionDetector, RetrievalPoisoningGuard
from chad.security.threat import SecurityThreat, ThreatCategory, ThreatLevel, ThreatModel
from chad.tools.permissions import PermissionEngine
from chad.tools.schema import ToolDefinition


@dataclass(slots=True)
class SecurityAuditLog:
    """Stores ordered security audit events."""

    events: list[dict[str, Any]] = field(default_factory=list)

    def log_event(self, event_type: str, details: dict[str, Any]) -> None:
        self.events.append(
            {
                "timestamp": time.time(),
                "event_type": event_type,
                "details": details,
            }
        )

    def clear(self) -> None:
        self.events.clear()


@dataclass(frozen=True, slots=True)
class SecurityCheckResult:
    allowed: bool
    threat_level: ThreatLevel
    sanitized_content: str
    reasons: tuple[str, ...]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "threat_level": self.threat_level.name,
            "sanitized_content": self.sanitized_content,
            "reasons": list(self.reasons),
            "metadata": self.metadata,
        }


class SecurityEngine:
    """Unified security engine for CHAD runtime enforcing threat evaluation, injection checks,

    exfiltration prevention, secret masking, sandbox guardrails, and tool permissions.
    """

    def __init__(
        self,
        threat_model: ThreatModel | None = None,
        injection_detector: PromptInjectionDetector | None = None,
        poisoning_guard: RetrievalPoisoningGuard | None = None,
        exfiltration_protection: ExfiltrationProtection | None = None,
        escape_guard: SandboxEscapeGuard | None = None,
        secret_scanner: SecretScanner | None = None,
        permission_engine: PermissionEngine | None = None,
    ) -> None:
        self.threat_model = threat_model or ThreatModel()
        self.injection_detector = injection_detector or PromptInjectionDetector()
        self.poisoning_guard = poisoning_guard or RetrievalPoisoningGuard()
        self.exfiltration_protection = exfiltration_protection or ExfiltrationProtection()
        self.escape_guard = escape_guard or SandboxEscapeGuard()
        self.secret_scanner = secret_scanner or SecretScanner()
        self.permission_engine = permission_engine or PermissionEngine()
        self.audit_log = SecurityAuditLog()

    def inspect_input(self, user_text: str) -> SecurityCheckResult:
        """Inspects incoming user prompts for injections and secrets."""
        if not user_text:
            return SecurityCheckResult(
                allowed=True,
                threat_level=ThreatLevel.LOW,
                sanitized_content="",
                reasons=(),
            )

        reasons: list[str] = []

        # Secret scan
        redacted_text, secrets_count = self.secret_scanner.redact_secrets(user_text)
        if secrets_count > 0:
            reasons.append(f"Detected and redacted {secrets_count} secret(s) in input.")
            self.audit_log.log_event("SECRET_REDACTED", {"count": secrets_count})

        # Injection scan
        inj_res = self.injection_detector.detect(redacted_text)
        sanitized = inj_res.sanitized_text
        threat_level = inj_res.threat_level

        if inj_res.is_injection:
            reasons.append(f"Prompt injection patterns detected: {', '.join(inj_res.matched_rules)}")
            threat = SecurityThreat(
                id=f"THR-{len(self.threat_model.get_threats())+1:04d}",
                category=ThreatCategory.PROMPT_INJECTION,
                level=inj_res.threat_level,
                description=f"Prompt injection in input: {inj_res.matched_rules}",
                source="user_input",
            )
            self.threat_model.record_threat(threat)
            self.audit_log.log_event("PROMPT_INJECTION_DETECTED", threat.to_dict())

        allowed = threat_level != ThreatLevel.CRITICAL

        return SecurityCheckResult(
            allowed=allowed,
            threat_level=threat_level,
            sanitized_content=sanitized,
            reasons=tuple(reasons),
        )

    def inspect_retrieved_content(self, chunk_text: str) -> SecurityCheckResult:
        """Inspects RAG / retrieved external evidence for poisoning attacks."""
        poison_res = self.poisoning_guard.inspect_chunk(chunk_text)

        if poison_res.is_poisoned:
            threat = SecurityThreat(
                id=f"THR-{len(self.threat_model.get_threats())+1:04d}",
                category=ThreatCategory.RETRIEVAL_POISONING,
                level=ThreatLevel.HIGH,
                description=f"Retrieval poisoning: {', '.join(poison_res.reasons)}",
                source="retrieved_content",
            )
            self.threat_model.record_threat(threat)
            self.audit_log.log_event("RETRIEVAL_POISONING_DETECTED", threat.to_dict())

        return SecurityCheckResult(
            allowed=True,
            threat_level=ThreatLevel.HIGH if poison_res.is_poisoned else ThreatLevel.LOW,
            sanitized_content=poison_res.cleaned_chunk,
            reasons=poison_res.reasons,
            metadata={"risk_score": poison_res.risk_score},
        )

    def inspect_command(self, command: str) -> SecurityCheckResult:
        """Inspects shell commands for sandbox escapes and path traversals."""
        esc_res = self.escape_guard.analyze_command(command)

        if esc_res.is_escape_attempt:
            threat = SecurityThreat(
                id=f"THR-{len(self.threat_model.get_threats())+1:04d}",
                category=ThreatCategory.SANDBOX_ESCAPE,
                level=ThreatLevel.CRITICAL,
                description=f"Sandbox escape attempt in command: {esc_res.detected_techniques}",
                source="command_execution",
            )
            self.threat_model.record_threat(threat)
            self.audit_log.log_event("SANDBOX_ESCAPE_BLOCKED", threat.to_dict())
            return SecurityCheckResult(
                allowed=False,
                threat_level=ThreatLevel.CRITICAL,
                sanitized_content="",
                reasons=esc_res.detected_techniques,
            )

        return SecurityCheckResult(
            allowed=True,
            threat_level=ThreatLevel.LOW,
            sanitized_content=command,
            reasons=(),
        )

    def inspect_exfiltration(self, url: str, payload: str | dict[str, Any] | None = None) -> SecurityCheckResult:
        """Inspects outbound URLs and payloads for exfiltration risks."""
        url_res = self.exfiltration_protection.analyze_url(url)
        payload_res = self.exfiltration_protection.analyze_payload(payload) if payload else None

        reasons = list(url_res.blocked_reasons)
        if payload_res:
            reasons.extend(payload_res.blocked_reasons)

        is_risk = url_res.is_risk or (payload_res.is_risk if payload_res else False)

        if is_risk:
            threat = SecurityThreat(
                id=f"THR-{len(self.threat_model.get_threats())+1:04d}",
                category=ThreatCategory.DATA_EXFILTRATION,
                level=ThreatLevel.HIGH,
                description=f"Exfiltration risk blocked: {', '.join(reasons)}",
                source="outbound_network",
            )
            self.threat_model.record_threat(threat)
            self.audit_log.log_event("DATA_EXFILTRATION_BLOCKED", threat.to_dict())

        return SecurityCheckResult(
            allowed=not is_risk,
            threat_level=ThreatLevel.HIGH if is_risk else ThreatLevel.LOW,
            sanitized_content=url_res.sanitized_url_or_payload,
            reasons=tuple(reasons),
        )

    def check_tool_permission(
        self,
        tool: ToolDefinition,
        user_role: str = "user",
        has_user_approval: bool = False,
    ) -> tuple[bool, str]:
        """Checks tool permissions through PermissionEngine and logs privilege audit events."""
        permitted, reason = self.permission_engine.is_permitted(tool, user_role, has_user_approval)
        if not permitted:
            self.audit_log.log_event(
                "TOOL_PERMISSION_DENIED",
                {"tool_id": tool.id, "user_role": user_role, "reason": reason},
            )
        return permitted, reason
