from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from chad.agent.coder import SecretScanner
from chad.agent.research import sanitize_untrusted_content
from chad.security.detectors import (
    DataExfiltrationDetector,
    PromptInjectionDetector,
    RetrievalPoisoningChecker,
    SandboxEscapeChecker,
)
from chad.security.threat_model import (
    SecurityPolicy,
    SecurityViolation,
    ThreatLevel,
)


def redact_secrets(text: str) -> str:
    if not text:
        return ""
    scanner = SecretScanner()
    redacted, _ = scanner.redact_secrets(text)
    return redacted


@dataclass(frozen=True, slots=True)
class SecurityAssessment:
    is_safe: bool
    max_threat_level: ThreatLevel
    violations: tuple[SecurityViolation, ...]
    sanitized_content: str
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "max_threat_level": self.max_threat_level.value,
            "violations": [v.to_dict() for v in self.violations],
            "sanitized_content": self.sanitized_content,
            "summary": self.summary,
        }


class SecurityEngine:
    """Unified security evaluation pipeline enforcing threat models and security policies across CHAD."""

    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self.policy = policy or SecurityPolicy()
        self.prompt_injection_detector = PromptInjectionDetector()
        self.retrieval_poisoning_checker = RetrievalPoisoningChecker()
        self.data_exfiltration_detector = DataExfiltrationDetector()
        self.sandbox_escape_checker = SandboxEscapeChecker()

    def _determine_max_threat(self, violations: list[SecurityViolation]) -> ThreatLevel:
        if not violations:
            return ThreatLevel.LOW
        sorted_violations = sorted(violations, key=lambda v: v.threat_level.score, reverse=True)
        return sorted_violations[0].threat_level

    def _is_safe(self, max_threat: ThreatLevel) -> bool:
        if max_threat == ThreatLevel.LOW:
            return True
        if self.policy.block_high_threats and max_threat.score >= ThreatLevel.HIGH.score:
            return False
        return max_threat.score <= self.policy.max_allowed_threat_level.score

    def evaluate_input(self, text: str, field_name: str = "input") -> SecurityAssessment:
        """Evaluates user or untrusted input text for prompt injections and secret leaks."""
        violations: list[SecurityViolation] = []

        injection_violations = self.prompt_injection_detector.scan(text, policy=self.policy)
        for v in injection_violations:
            violations.append(
                SecurityViolation(
                    category=v.category,
                    threat_level=v.threat_level,
                    description=v.description,
                    evidence=v.evidence,
                    target_field=field_name,
                )
            )

        secret_violations = self.data_exfiltration_detector.scan_text_for_secrets(text)
        for v in secret_violations:
            violations.append(
                SecurityViolation(
                    category=v.category,
                    threat_level=v.threat_level,
                    description=v.description,
                    evidence=v.evidence,
                    target_field=field_name,
                )
            )

        max_threat = self._determine_max_threat(violations)
        safe = self._is_safe(max_threat)
        sanitized = self.sanitize_text(text)

        summary = (
            f"Input is safe. (Threat Level: {max_threat.value})"
            if safe
            else f"Input blocked due to {len(violations)} security violation(s). Highest threat: {max_threat.value}"
        )

        return SecurityAssessment(
            is_safe=safe,
            max_threat_level=max_threat,
            violations=tuple(violations),
            sanitized_content=sanitized,
            summary=summary,
        )

    def evaluate_retrieved_content(self, text: str, source_url: str = "") -> SecurityAssessment:
        """Scans external RAG/web fetched documents for prompt poisoning and hidden injection attacks."""
        violations: list[SecurityViolation] = []

        poison_violations = self.retrieval_poisoning_checker.scan(text)
        violations.extend(poison_violations)

        injection_violations = self.prompt_injection_detector.scan(text, policy=self.policy)
        violations.extend(injection_violations)

        max_threat = self._determine_max_threat(violations)
        safe = self._is_safe(max_threat)
        sanitized = sanitize_untrusted_content(text)

        summary = (
            f"Retrieved content from '{source_url or 'source'}' passed security checks."
            if safe
            else f"Retrieved content from '{source_url or 'source'}' blocked due to security violations."
        )

        return SecurityAssessment(
            is_safe=safe,
            max_threat_level=max_threat,
            violations=tuple(violations),
            sanitized_content=sanitized,
            summary=summary,
        )

    def evaluate_tool_execution(
        self, tool_name: str, arguments: dict[str, Any]
    ) -> SecurityAssessment:
        """Evaluates tool invocation parameters for sandbox escape, exfiltration target domains, and secrets."""
        violations: list[SecurityViolation] = []

        for arg_key, arg_val in arguments.items():
            str_val = str(arg_val)

            # Check for secrets
            sec_v = self.data_exfiltration_detector.scan_text_for_secrets(str_val)
            violations.extend(sec_v)

            # Check for escape attempts in code/commands/file paths
            esc_v = self.sandbox_escape_checker.scan(str_val)
            violations.extend(esc_v)

            # Check URLs for exfiltration
            if "url" in arg_key.lower() or str_val.startswith(("http://", "https://")):
                url_v = self.data_exfiltration_detector.scan_outbound_url(str_val, self.policy)
                violations.extend(url_v)

        max_threat = self._determine_max_threat(violations)
        safe = self._is_safe(max_threat)

        summary = (
            f"Tool '{tool_name}' execution arguments passed security inspection."
            if safe
            else f"Tool '{tool_name}' execution blocked due to security violations."
        )

        return SecurityAssessment(
            is_safe=safe,
            max_threat_level=max_threat,
            violations=tuple(violations),
            sanitized_content=str(arguments),
            summary=summary,
        )

    def evaluate_output(self, text: str) -> SecurityAssessment:
        """Evaluates assistant output prior to presenting to user or executing actions."""
        violations: list[SecurityViolation] = []

        secret_violations = self.data_exfiltration_detector.scan_text_for_secrets(text)
        violations.extend(secret_violations)

        max_threat = self._determine_max_threat(violations)
        safe = self._is_safe(max_threat)
        sanitized = redact_secrets(text)

        summary = (
            "Model output passed security checks."
            if safe
            else f"Model output contained {len(violations)} security violation(s) and was sanitized."
        )

        return SecurityAssessment(
            is_safe=safe,
            max_threat_level=max_threat,
            violations=tuple(violations),
            sanitized_content=sanitized,
            summary=summary,
        )

    def sanitize_text(self, text: str) -> str:
        """Redacts secrets and sanitizes untrusted markup tags from text."""
        if not text:
            return ""
        return redact_secrets(text)
