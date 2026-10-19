from __future__ import annotations


from chad.security.exfiltration import ExfiltrationGuard
from chad.security.injection import PromptInjectionDetector
from chad.security.models import (
    SecurityAction,
    ThreatAssessment,
    ThreatLevel,
)
from chad.security.sandbox_guard import SandboxEscapeGuard


class SecurityEngine:
    """Unified security subsystem evaluating prompts, context, outputs, and tool operations."""

    def __init__(
        self,
        injection_detector: PromptInjectionDetector | None = None,
        exfiltration_guard: ExfiltrationGuard | None = None,
        sandbox_guard: SandboxEscapeGuard | None = None,
    ) -> None:
        self.injection_detector = injection_detector or PromptInjectionDetector()
        self.exfiltration_guard = exfiltration_guard or ExfiltrationGuard()
        self.sandbox_guard = sandbox_guard or SandboxEscapeGuard()

    def inspect_user_input(self, user_input: str) -> ThreatAssessment:
        """Evaluates incoming user messages for prompt injections or jailbreak attempts."""
        return self.injection_detector.detect_prompt_injection(user_input)

    def inspect_retrieved_context(
        self, content: str, source: str = "retrieved_doc"
    ) -> ThreatAssessment:
        """Evaluates retrieved RAG chunks, web content, or tool outputs for indirect prompt injection."""
        return self.injection_detector.detect_retrieval_poisoning(content, source=source)

    def inspect_assistant_output(self, output: str) -> ThreatAssessment:
        """Evaluates assistant output for secret leaks or covert exfiltration channels."""
        secret_assessment = self.exfiltration_guard.check_output_for_secrets(output)
        if secret_assessment.is_threat:
            return secret_assessment

        exfil_assessment = self.exfiltration_guard.check_exfiltration_channels(output)
        if exfil_assessment.is_threat:
            return exfil_assessment

        return ThreatAssessment(
            is_threat=False,
            threat_level=ThreatLevel.NONE,
            category=None,
            confidence=0.0,
            description="Assistant output passed security checks.",
            suggested_action=SecurityAction.ALLOW,
        )

    def inspect_command_execution(self, command: str) -> ThreatAssessment:
        """Evaluates command string for sandbox escape attempts or dangerous actions."""
        return self.sandbox_guard.validate_command(command)

    def inspect_file_access(self, file_path: str) -> ThreatAssessment:
        """Evaluates file path access for sandbox containment violations."""
        return self.sandbox_guard.validate_path_access(file_path)

    def evaluate_request(
        self,
        user_input: str | None = None,
        retrieved_contexts: list[dict[str, str]] | None = None,
        command: str | None = None,
        file_path: str | None = None,
    ) -> list[ThreatAssessment]:
        """Runs batch evaluation over multiple interaction vectors and returns all detected threats."""
        threats: list[ThreatAssessment] = []

        if user_input:
            assess = self.inspect_user_input(user_input)
            if assess.is_threat:
                threats.append(assess)

        if retrieved_contexts:
            for ctx in retrieved_contexts:
                content = ctx.get("content", "")
                source = ctx.get("source", "retrieved_doc")
                assess = self.inspect_retrieved_context(content, source=source)
                if assess.is_threat:
                    threats.append(assess)

        if command:
            assess = self.inspect_command_execution(command)
            if assess.is_threat:
                threats.append(assess)

        if file_path:
            assess = self.inspect_file_access(file_path)
            if assess.is_threat:
                threats.append(assess)

        return threats
