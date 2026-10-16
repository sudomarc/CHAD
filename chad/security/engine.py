from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chad.security.detector import PromptInjectionDetector
from chad.security.exfiltration import DataExfiltrationGuard
from chad.security.sandbox_guard import SandboxEscapeGuard
from chad.security.threat_model import ActionRecommendation, RiskLevel, ThreatAssessment, ThreatModel


@dataclass(frozen=True, slots=True)
class SecurityReport:
    assessments: tuple[ThreatAssessment, ...]
    max_risk_level: RiskLevel
    max_score: float
    recommendation: ActionRecommendation
    is_safe: bool
    sanitized_text: str = ""
    summary: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_risk_level": self.max_risk_level.value,
            "max_score": self.max_score,
            "recommendation": self.recommendation.value,
            "is_safe": self.is_safe,
            "sanitized_text": self.sanitized_text,
            "summary": self.summary,
            "assessments": [
                {
                    "category": a.category.value,
                    "risk_level": a.risk_level.value,
                    "score": a.score,
                    "description": a.description,
                    "recommendation": a.recommendation.value,
                    "metadata": a.metadata,
                }
                for a in self.assessments
            ],
        }


class SecurityEngine:
    """Unified security coordinator for threat modeling, prompt injection, exfiltration, and sandbox escape guard checks."""

    def __init__(
        self,
        threat_model: ThreatModel | None = None,
        injection_detector: PromptInjectionDetector | None = None,
        exfiltration_guard: DataExfiltrationGuard | None = None,
        sandbox_guard: SandboxEscapeGuard | None = None,
    ) -> None:
        self.threat_model = threat_model or ThreatModel()
        self.injection_detector = injection_detector or PromptInjectionDetector(self.threat_model)
        self.exfiltration_guard = exfiltration_guard or DataExfiltrationGuard(self.threat_model)
        self.sandbox_guard = sandbox_guard or SandboxEscapeGuard(self.threat_model)

    def audit_input(self, text: str) -> SecurityReport:
        """Audits user input or incoming prompts."""
        inj_assessment = self.injection_detector.analyze(text)
        exf_assessment = self.exfiltration_guard.analyze(text)
        sanitized = self.injection_detector.sanitize(text)

        return self._build_report((inj_assessment, exf_assessment), sanitized_text=sanitized)

    def audit_retrieved_content(self, content: str) -> SecurityReport:
        """Audits untrusted external web pages, files, or retrieved context."""
        inj_assessment = self.injection_detector.analyze(content)
        exf_assessment = self.exfiltration_guard.analyze(content)
        sanitized = self.injection_detector.sanitize(content)

        return self._build_report((inj_assessment, exf_assessment), sanitized_text=sanitized)

    def audit_command(self, command_or_code: str) -> SecurityReport:
        """Audits shell commands or code before sandboxed execution."""
        sb_assessment = self.sandbox_guard.analyze(command_or_code)
        exf_assessment = self.exfiltration_guard.analyze(command_or_code)

        return self._build_report((sb_assessment, exf_assessment), sanitized_text=command_or_code)

    def audit_output(self, text: str) -> SecurityReport:
        """Audits generated model output before rendering to user or tool execution."""
        exf_assessment = self.exfiltration_guard.analyze(text)
        inj_assessment = self.injection_detector.analyze(text)
        sanitized = self.injection_detector.sanitize(text)

        return self._build_report((exf_assessment, inj_assessment), sanitized_text=sanitized)

    def _build_report(
        self,
        assessments: tuple[ThreatAssessment, ...],
        sanitized_text: str = "",
    ) -> SecurityReport:
        if not assessments:
            return SecurityReport(
                assessments=(),
                max_risk_level=RiskLevel.NONE,
                max_score=0.0,
                recommendation=ActionRecommendation.ALLOW,
                is_safe=True,
                sanitized_text=sanitized_text,
                summary="No assessments performed",
            )

        max_score = max(a.score for a in assessments)

        # Determine highest risk level
        risk_priority = {
            RiskLevel.CRITICAL: 4,
            RiskLevel.HIGH: 3,
            RiskLevel.MEDIUM: 2,
            RiskLevel.LOW: 1,
            RiskLevel.NONE: 0,
        }
        max_risk = max((a.risk_level for a in assessments), key=lambda r: risk_priority[r])

        # Determine recommendation
        rec_priority = {
            ActionRecommendation.BLOCK: 3,
            ActionRecommendation.QUARANTINE: 2,
            ActionRecommendation.WARN: 1,
            ActionRecommendation.ALLOW: 0,
        }
        overall_rec = max((a.recommendation for a in assessments), key=lambda r: rec_priority[r])

        is_safe = overall_rec in (ActionRecommendation.ALLOW, ActionRecommendation.WARN)

        flagged = [a.description for a in assessments if a.score > 0.0]
        summary = "; ".join(flagged) if flagged else "All checks passed"

        return SecurityReport(
            assessments=assessments,
            max_risk_level=max_risk,
            max_score=max_score,
            recommendation=overall_rec,
            is_safe=is_safe,
            sanitized_text=sanitized_text,
            summary=summary,
        )
