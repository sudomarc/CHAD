from __future__ import annotations

import logging
from typing import Any

from chad.security.exfiltration import ExfiltrationGuard
from chad.security.injection import PromptInjectionDetector
from chad.security.models import (
    SecurityCheckResult,
    SecurityPolicy,
    SecurityViolation,
    ThreatLevel,
)
from chad.security.sandbox import SandboxEscapeGuard

logger = logging.getLogger("chad.security")


class SecurityEngine:
    """Unified security engine for CHAD agent runtime.

    Provides threat modeling, prompt injection detection, exfiltration protection,
    sandbox escape guards, and audit logging.
    """

    def __init__(self, policy: SecurityPolicy | None = None) -> None:
        self.policy = policy or SecurityPolicy()
        self.injection_detector = PromptInjectionDetector()
        self.exfiltration_guard = ExfiltrationGuard(allowed_domains=self.policy.allowed_domains)
        self.sandbox_guard = SandboxEscapeGuard()
        self.audit_log: list[dict[str, Any]] = []

    def evaluate_input_prompt(self, prompt: str) -> SecurityCheckResult:
        """Evaluates user input prompt for threats before sending to models."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if self.policy.enable_injection_detection:
            inj_res = self.injection_detector.detect_prompt_injection(prompt)
            violations.extend(inj_res.violations)
            max_threat = max(max_threat, inj_res.max_threat_level)

        if self.policy.enable_exfiltration_guard:
            exfil_res = self.exfiltration_guard.check_for_secrets(prompt)
            violations.extend(exfil_res.violations)
            max_threat = max(max_threat, exfil_res.max_threat_level)

        passed = max_threat < self.policy.block_threshold
        if self.policy.strict_mode and violations:
            passed = False

        sanitized = prompt
        if self.policy.enable_exfiltration_guard:
            sanitized = self.exfiltration_guard.redact_secrets(sanitized)
        if self.policy.enable_injection_detection and not passed:
            sanitized = self.injection_detector.sanitize_untrusted_prompt(sanitized)

        result = SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=sanitized,
            metadata={"phase": "input_prompt", "strict_mode": self.policy.strict_mode},
        )

        self._record_audit("evaluate_input_prompt", result)
        return result

    def evaluate_retrieved_context(
        self, context: str, source_id: str | None = None
    ) -> SecurityCheckResult:
        """Evaluates RAG/file retrieved content for indirect prompt injection or poisoning."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if self.policy.enable_injection_detection:
            poison_res = self.injection_detector.detect_retrieval_poisoning(
                context, source_id=source_id
            )
            violations.extend(poison_res.violations)
            max_threat = max(max_threat, poison_res.max_threat_level)

        if self.policy.enable_exfiltration_guard:
            sec_res = self.exfiltration_guard.check_for_secrets(context)
            violations.extend(sec_res.violations)
            max_threat = max(max_threat, sec_res.max_threat_level)

        passed = max_threat < self.policy.block_threshold
        if self.policy.strict_mode and violations:
            passed = False

        sanitized = context
        if self.policy.enable_exfiltration_guard:
            sanitized = self.exfiltration_guard.redact_secrets(sanitized)
        if self.policy.enable_injection_detection and not passed:
            sanitized = self.injection_detector.sanitize_untrusted_prompt(sanitized)

        result = SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=sanitized,
            metadata={"phase": "retrieved_context", "source_id": source_id},
        )

        self._record_audit("evaluate_retrieved_context", result)
        return result

    def evaluate_model_output(self, output: str) -> SecurityCheckResult:
        """Evaluates LLM generated output for secret leaks or exfiltration triggers."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if self.policy.enable_exfiltration_guard:
            exfil_res = self.exfiltration_guard.check_exfiltration(output)
            violations.extend(exfil_res.violations)
            max_threat = max(max_threat, exfil_res.max_threat_level)

        passed = max_threat < self.policy.block_threshold
        if self.policy.strict_mode and violations:
            passed = False

        sanitized = output
        if self.policy.enable_exfiltration_guard:
            sanitized = self.exfiltration_guard.redact_secrets(sanitized)

        result = SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=sanitized,
            metadata={"phase": "model_output"},
        )

        self._record_audit("evaluate_model_output", result)
        return result

    def evaluate_command_execution(
        self, command: str, root_dir: str | None = None
    ) -> SecurityCheckResult:
        """Evaluates command string prior to sandbox execution."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if self.policy.enable_sandbox_guard:
            cmd_res = self.sandbox_guard.validate_command(command)
            violations.extend(cmd_res.violations)
            max_threat = max(max_threat, cmd_res.max_threat_level)

        passed = max_threat < self.policy.block_threshold
        if self.policy.strict_mode and violations:
            passed = False

        result = SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=command,
            metadata={"phase": "command_execution", "root_dir": root_dir},
        )

        self._record_audit("evaluate_command_execution", result)
        return result

    def evaluate_file_access(
        self, target_path: str, root_dir: str | None = None
    ) -> SecurityCheckResult:
        """Evaluates path for file access security."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if self.policy.enable_sandbox_guard:
            path_res = self.sandbox_guard.validate_path(target_path, root_dir=root_dir)
            violations.extend(path_res.violations)
            max_threat = max(max_threat, path_res.max_threat_level)

        passed = max_threat < self.policy.block_threshold
        if self.policy.strict_mode and violations:
            passed = False

        result = SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=target_path,
            metadata={"phase": "file_access", "target_path": target_path, "root_dir": root_dir},
        )

        self._record_audit("evaluate_file_access", result)
        return result

    def _record_audit(self, action: str, result: SecurityCheckResult) -> None:
        event = {
            "action": action,
            "passed": result.passed,
            "max_threat_level": result.max_threat_level.value,
            "violation_count": len(result.violations),
            "violations": [v.to_dict() for v in result.violations],
            "metadata": dict(result.metadata),
        }
        self.audit_log.append(event)
        if not result.passed:
            logger.warning("Security policy violation in %s: %s", action, event)
