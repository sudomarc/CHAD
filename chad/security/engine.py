from __future__ import annotations

from typing import Any

from chad.security.detectors import (
    ExfiltrationGuard,
    PromptInjectionDetector,
    RetrievalPoisoningGuard,
    SandboxEscapeGuard,
    SecretHandlingGuard,
)
from chad.security.models import (
    SecurityCheckResult,
    ThreatFinding,
)


class SecurityEngine:
    """Unified security engine coordinating threat detection, prompt injection defense,
    retrieval protection, secret redaction, exfiltration prevention, and sandbox safety.
    """

    def __init__(self) -> None:
        self.injection_detector = PromptInjectionDetector()
        self.retrieval_guard = RetrievalPoisoningGuard()
        self.exfiltration_guard = ExfiltrationGuard()
        self.sandbox_guard = SandboxEscapeGuard()
        self.secret_guard = SecretHandlingGuard()

    def check_user_input(self, text: str) -> SecurityCheckResult:
        """Analyzes incoming user prompts for injection and secret leakage."""
        inj_res = self.injection_detector.analyze(text)
        sec_res = self.secret_guard.scan_and_redact(inj_res.sanitized_content or text)

        all_findings: list[ThreatFinding] = list(inj_res.findings) + list(sec_res.findings)
        is_safe = inj_res.is_safe and sec_res.is_safe

        return SecurityCheckResult(
            is_safe=is_safe,
            findings=tuple(all_findings),
            sanitized_content=sec_res.sanitized_content,
        )

    def check_retrieved_content(self, content: str, source_id: str = "") -> SecurityCheckResult:
        """Checks retrieved documents or web content for prompt injection or poison attacks."""
        return self.retrieval_guard.inspect_retrieved_content(content, source_id=source_id)

    def check_outbound_tool_call(self, tool_name: str, tool_args: dict[str, Any]) -> SecurityCheckResult:
        """Inspects outbound tool calls for data exfiltration attempts."""
        arg_str = str(tool_args)
        exf_res = self.exfiltration_guard.check_outbound(arg_str, payload_summary=f"Tool: {tool_name}")
        sec_res = self.secret_guard.scan_and_redact(arg_str)

        all_findings = list(exf_res.findings) + list(sec_res.findings)
        return SecurityCheckResult(
            is_safe=exf_res.is_safe and sec_res.is_safe,
            findings=tuple(all_findings),
            sanitized_content=exf_res.sanitized_content if not exf_res.is_safe else None,
        )

    def check_code_execution(self, code: str) -> SecurityCheckResult:
        """Verifies code safety prior to sandbox execution."""
        return self.sandbox_guard.inspect_code(code)

    def check_model_output(self, output: str) -> SecurityCheckResult:
        """Ensures generated model outputs do not leak secrets or unsafe instructions."""
        return self.secret_guard.scan_and_redact(output)
