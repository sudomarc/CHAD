from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from chad.security.detector import InjectionCheckResult, PromptInjectionDetector
from chad.security.exfiltration import DataExfiltrationGuard, ExfiltrationCheckResult
from chad.security.sandbox_guard import SandboxCheckResult, SandboxEscapeGuard
from chad.security.threat_model import (
    SecurityRiskLevel,
    ThreatAssessment,
    ThreatCategory,
    ThreatModel,
)


@dataclass(frozen=True, slots=True)
class SecurityAuditResult:
    passed: bool
    overall_risk_level: SecurityRiskLevel
    threat_assessments: list[ThreatAssessment] = field(default_factory=list)
    injection_result: InjectionCheckResult | None = None
    exfiltration_result: ExfiltrationCheckResult | None = None
    sandbox_result: SandboxCheckResult | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "overall_risk_level": self.overall_risk_level.value,
            "threat_assessments": [t.to_dict() for t in self.threat_assessments],
            "injection_result": self.injection_result.to_dict() if self.injection_result else None,
            "exfiltration_result": self.exfiltration_result.to_dict()
            if self.exfiltration_result
            else None,
            "sandbox_result": self.sandbox_result.to_dict() if self.sandbox_result else None,
        }


class SecurityEngine:
    """Unified security evaluation coordinator for prompts, retrieved content, tools, and sandbox actions."""

    def __init__(
        self,
        injection_detector: PromptInjectionDetector | None = None,
        exfiltration_guard: DataExfiltrationGuard | None = None,
        sandbox_guard: SandboxEscapeGuard | None = None,
    ) -> None:
        self.injection_detector = injection_detector or PromptInjectionDetector()
        self.exfiltration_guard = exfiltration_guard or DataExfiltrationGuard()
        self.sandbox_guard = sandbox_guard or SandboxEscapeGuard()

    def audit_input_prompt(self, user_prompt: str) -> SecurityAuditResult:
        """Audits incoming user input for injection threats and secrets."""
        model = ThreatModel()

        inj_res = self.injection_detector.check_text(user_prompt)
        if inj_res.is_injection:
            model.add_threat(
                ThreatAssessment(
                    category=ThreatCategory.PROMPT_INJECTION,
                    risk_level=inj_res.risk_level,
                    title="Prompt Injection Detected",
                    description=f"Prompt injection patterns detected: {', '.join(inj_res.detected_patterns)}",
                    mitigation="Sanitize user prompt or deny execution.",
                )
            )

        exf_res = self.exfiltration_guard.check_content(user_prompt)
        if exf_res.is_exfiltration_risk:
            model.add_threat(
                ThreatAssessment(
                    category=ThreatCategory.SECRET_LEAKAGE,
                    risk_level=exf_res.risk_level,
                    title="Potential Secret Exposure",
                    description=f"Secrets or suspicious links in input: {', '.join(exf_res.suspicious_patterns)}",
                    mitigation="Redact secrets prior to LLM submission.",
                )
            )

        max_risk = model.evaluate_max_risk()
        passed = max_risk in (SecurityRiskLevel.NONE, SecurityRiskLevel.LOW)

        return SecurityAuditResult(
            passed=passed,
            overall_risk_level=max_risk,
            threat_assessments=model.assessments,
            injection_result=inj_res,
            exfiltration_result=exf_res,
        )

    def audit_retrieved_context(self, retrieved_text: str) -> SecurityAuditResult:
        """Audits retrieved documents/chunks for indirect retrieval poisoning and exfiltration links."""
        model = ThreatModel()

        inj_res = self.injection_detector.check_retrieved_content(retrieved_text)
        if inj_res.is_injection:
            model.add_threat(
                ThreatAssessment(
                    category=ThreatCategory.RETRIEVAL_POISONING,
                    risk_level=inj_res.risk_level,
                    title="Retrieval Poisoning Attack Detected",
                    description=f"Poisoned content detected in retrieved document: {', '.join(inj_res.detected_patterns)}",
                    mitigation="Filter or redact untrusted retrieved chunks before context assembly.",
                )
            )

        exf_res = self.exfiltration_guard.check_content(retrieved_text)
        if exf_res.is_exfiltration_risk:
            model.add_threat(
                ThreatAssessment(
                    category=ThreatCategory.DATA_EXFILTRATION,
                    risk_level=exf_res.risk_level,
                    title="Exfiltration URL in Retrieved Document",
                    description=f"Suspicious tracking or egress URL in retrieved content: {', '.join(exf_res.suspicious_patterns)}",
                    mitigation="Strip tracking tags and URLs from retrieved text.",
                )
            )

        max_risk = model.evaluate_max_risk()
        passed = max_risk in (SecurityRiskLevel.NONE, SecurityRiskLevel.LOW)

        return SecurityAuditResult(
            passed=passed,
            overall_risk_level=max_risk,
            threat_assessments=model.assessments,
            injection_result=inj_res,
            exfiltration_result=exf_res,
        )

    def audit_command_or_path(self, command_or_path: str) -> SecurityAuditResult:
        """Audits commands or workspace paths for sandbox escape, path traversal, or privilege escalation."""
        model = ThreatModel()

        sb_res = self.sandbox_guard.check_command_or_path(command_or_path)
        if not sb_res.is_safe:
            model.add_threat(
                ThreatAssessment(
                    category=ThreatCategory.SANDBOX_ESCAPE
                    if "traversal" in " ".join(sb_res.violations).lower()
                    else ThreatCategory.PRIVILEGE_ESCALATION,
                    risk_level=sb_res.risk_level,
                    title="Sandbox Boundary Violation",
                    description=f"Command or path security violations: {', '.join(sb_res.violations)}",
                    mitigation="Block command execution or reject path outside workspace.",
                )
            )

        max_risk = model.evaluate_max_risk()
        passed = sb_res.is_safe

        return SecurityAuditResult(
            passed=passed,
            overall_risk_level=max_risk,
            threat_assessments=model.assessments,
            sandbox_result=sb_res,
        )
