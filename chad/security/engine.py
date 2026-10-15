from __future__ import annotations

from dataclasses import dataclass, field

from chad.security.exfiltration import ExfiltrationGuard, ExfiltrationFinding
from chad.security.prompt_injection import PromptInjectionDetector, InjectionAnalysis
from chad.security.sandbox import SandboxGuard, SandboxViolation
from chad.security.threat_model import ThreatModel, ThreatAssessment, RiskLevel


@dataclass(slots=True)
class SecurityCheckResult:
    is_safe: bool
    risk_level: RiskLevel
    assessment: ThreatAssessment
    injection_analysis: InjectionAnalysis | None = None
    exfiltration_findings: list[ExfiltrationFinding] = field(default_factory=list)
    sandbox_violations: list[SandboxViolation] = field(default_factory=list)
    sanitized_content: str | None = None
    redacted_content: str | None = None


class SecurityEngine:
    """Unified security engine coordinating threat modeling, injection detection, exfiltration protection, and sandbox guards."""

    def __init__(
        self,
        threat_model: ThreatModel | None = None,
        injection_detector: PromptInjectionDetector | None = None,
        exfiltration_guard: ExfiltrationGuard | None = None,
        sandbox_guard: SandboxGuard | None = None,
    ) -> None:
        self.threat_model = threat_model or ThreatModel()
        self.injection_detector = injection_detector or PromptInjectionDetector()
        self.exfiltration_guard = exfiltration_guard or ExfiltrationGuard()
        self.sandbox_guard = sandbox_guard or SandboxGuard()

    def inspect_input(self, text: str, source: str = "user") -> SecurityCheckResult:
        assessment = self.threat_model.evaluate_text(text)
        injection_analysis = self.injection_detector.analyze(text)
        secrets = self.exfiltration_guard.scan_secrets(text)
        redacted = self.exfiltration_guard.redact_secrets(text)

        sanitized = None
        if source != "user" or injection_analysis.is_injection_detected:
            sanitized = self.injection_detector.sanitize_untrusted_input(text)

        is_safe = assessment.is_safe and not injection_analysis.is_injection_detected and len(secrets) == 0

        return SecurityCheckResult(
            is_safe=is_safe,
            risk_level=assessment.risk_level,
            assessment=assessment,
            injection_analysis=injection_analysis,
            exfiltration_findings=secrets,
            sanitized_content=sanitized,
            redacted_content=redacted,
        )

    def inspect_output(self, text: str) -> SecurityCheckResult:
        assessment = self.threat_model.evaluate_text(text)
        secrets = self.exfiltration_guard.scan_secrets(text)
        redacted = self.exfiltration_guard.redact_secrets(text)

        is_safe = len(secrets) == 0

        return SecurityCheckResult(
            is_safe=is_safe,
            risk_level=assessment.risk_level,
            assessment=assessment,
            exfiltration_findings=secrets,
            redacted_content=redacted,
        )

    def inspect_tool_call(
        self,
        tool_name: str,
        arguments: dict,
        workspace_root: str | None = None,
    ) -> SecurityCheckResult:
        assessment = self.threat_model.evaluate_tool_execution(tool_name, arguments)
        violations: list[SandboxViolation] = []

        if "command" in arguments:
            violations.extend(self.sandbox_guard.validate_command(str(arguments["command"])))

        for k in ("path", "filepath", "filename", "file"):
            if k in arguments:
                violations.extend(self.sandbox_guard.validate_path(str(arguments[k]), workspace_root=workspace_root))

        is_safe = assessment.is_safe and len(violations) == 0

        return SecurityCheckResult(
            is_safe=is_safe,
            risk_level=RiskLevel.CRITICAL if len(violations) > 0 else assessment.risk_level,
            assessment=assessment,
            sandbox_violations=violations,
        )

    def inspect_retrieved_content(self, content: str) -> SecurityCheckResult:
        assessment = self.threat_model.evaluate_text(content)
        injection_analysis = self.injection_detector.analyze(content)
        sanitized = self.injection_detector.sanitize_untrusted_input(content)

        return SecurityCheckResult(
            is_safe=not injection_analysis.is_injection_detected,
            risk_level=assessment.risk_level,
            assessment=assessment,
            injection_analysis=injection_analysis,
            sanitized_content=sanitized,
        )

    def redact_secrets(self, text: str) -> str:
        return self.exfiltration_guard.redact_secrets(text)

    def sanitize_content(self, text: str) -> str:
        return self.injection_detector.sanitize_untrusted_input(text)
