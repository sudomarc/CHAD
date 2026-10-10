from __future__ import annotations

import re
import time
from pathlib import Path

from chad.security.exfiltration import DataExfiltrationDetector, ExfiltrationChannel, SecretPolicy
from chad.security.injection import InjectionDetectionResult, PromptInjectionDetector
from chad.security.threat_model import SecurityAssessment, ThreatCategory, ThreatModel
from chad.tools.permissions import ToolPermissionLevel


class SandboxEscapeChecker:
    """Inspects file paths and commands for sandbox escape or traversal vulnerabilities."""

    FORBIDDEN_COMMAND_PATTERNS: list[re.Pattern[str]] = [
        re.compile(r"\brm\s+-rf\s+/", re.IGNORECASE),
        re.compile(r"\bsudo\b", re.IGNORECASE),
        re.compile(r"\|\s*(?:ba)?sh\b", re.IGNORECASE),
        re.compile(r"\b(?:curl|wget)\b.*\|\s*(?:ba)?sh\b", re.IGNORECASE),
        re.compile(r"\bchmod\s+777\b", re.IGNORECASE),
        re.compile(r"\bchown\b", re.IGNORECASE),
        re.compile(r"\b(?:nc|netcat|ncat)\s+-e\b", re.IGNORECASE),
    ]

    def validate_file_path(self, target_path: str | Path, workspace_root: str | Path) -> tuple[bool, str]:
        """Verifies that target_path remains strictly within workspace_root."""
        root = Path(workspace_root).resolve()
        try:
            resolved = (root / target_path).resolve()
            resolved.relative_to(root)
            return True, "Path is within workspace sandbox"
        except ValueError:
            return False, f"Sandbox escape blocked: '{target_path}' resolves outside workspace root '{root}'."

    def validate_command(self, command: str) -> tuple[bool, str]:
        """Checks command string for dangerous sandbox escape patterns."""
        if not command or not command.strip():
            return False, "Empty command string"

        cleaned = command.strip()
        for pattern in self.FORBIDDEN_COMMAND_PATTERNS:
            if pattern.search(cleaned):
                return False, f"Dangerous command blocked: matched pattern '{pattern.pattern}'"

        return True, "Command passed sandbox escape validation"


class LeastPrivilegePolicy:
    """Enforces minimum privilege requirements and access control rules."""

    def __init__(
        self,
        max_allowed_permission: ToolPermissionLevel = ToolPermissionLevel.USER_APPROVAL,
        allow_network: bool = True,
        restricted_paths: list[str] | None = None,
    ) -> None:
        self.max_allowed_permission = max_allowed_permission
        self.allow_network = allow_network
        self.restricted_paths = restricted_paths or ["/etc", "/var", "/usr", "/root", "~/.ssh"]

    def is_tool_permitted(self, required_level: ToolPermissionLevel) -> tuple[bool, str]:
        """Checks if tool permission level is permitted under current policy."""
        hierarchy = {
            ToolPermissionLevel.ALWAYS_ALLOW: 1,
            ToolPermissionLevel.USER_APPROVAL: 2,
            ToolPermissionLevel.ADMIN_ONLY: 3,
            ToolPermissionLevel.BLOCKED: 4,
        }

        req_score = hierarchy.get(required_level, 99)
        max_score = hierarchy.get(self.max_allowed_permission, 1)

        if req_score > max_score:
            return False, f"Permission denied: tool requires level '{required_level.value}', maximum allowed is '{self.max_allowed_permission.value}'."
        return True, "Tool permission granted"

    def is_path_restricted(self, path_str: str) -> bool:
        """Checks if a path hits system restricted directories."""
        normalized = str(Path(path_str).expanduser().resolve())
        for restricted in self.restricted_paths:
            if normalized.startswith(restricted):
                return True
        return False


class AbuseControl:
    """Monitors request volume, error bursts, and execution limits to mitigate abuse."""

    def __init__(
        self,
        max_requests_per_minute: int = 60,
        max_errors_per_minute: int = 15,
    ) -> None:
        self.max_requests_per_minute = max_requests_per_minute
        self.max_errors_per_minute = max_errors_per_minute
        self._request_timestamps: list[float] = []
        self._error_timestamps: list[float] = []

    def record_request(self) -> tuple[bool, str]:
        """Records a request and checks rate limits."""
        now = time.time()
        self._request_timestamps = [t for t in self._request_timestamps if now - t <= 60.0]
        if len(self._request_timestamps) >= self.max_requests_per_minute:
            return False, f"Rate limit exceeded: >{self.max_requests_per_minute} requests/minute."
        self._request_timestamps.append(now)
        return True, "Request permitted"

    def record_error(self) -> tuple[bool, str]:
        """Records an error and checks error burst limits."""
        now = time.time()
        self._error_timestamps = [t for t in self._error_timestamps if now - t <= 60.0]
        if len(self._error_timestamps) >= self.max_errors_per_minute:
            return False, f"Error burst limit exceeded: >{self.max_errors_per_minute} errors/minute."
        self._error_timestamps.append(now)
        return True, "Error within limits"

    def reset(self) -> None:
        self._request_timestamps.clear()
        self._error_timestamps.clear()


class SecurityEngine:
    """Unified security manager for CHAD agent runtime."""

    def __init__(
        self,
        threat_model: ThreatModel | None = None,
        injection_detector: PromptInjectionDetector | None = None,
        exfiltration_detector: DataExfiltrationDetector | None = None,
        secret_policy: SecretPolicy | None = None,
        sandbox_checker: SandboxEscapeChecker | None = None,
        privilege_policy: LeastPrivilegePolicy | None = None,
        abuse_control: AbuseControl | None = None,
    ) -> None:
        self.threat_model = threat_model or ThreatModel()
        self.injection_detector = injection_detector or PromptInjectionDetector()
        self.exfiltration_detector = exfiltration_detector or DataExfiltrationDetector()
        self.secret_policy = secret_policy or SecretPolicy()
        self.sandbox_checker = sandbox_checker or SandboxEscapeChecker()
        self.privilege_policy = privilege_policy or LeastPrivilegePolicy()
        self.abuse_control = abuse_control or AbuseControl()

    def inspect_user_input(self, text: str) -> InjectionDetectionResult:
        """Inspects incoming user prompt for prompt injection threats."""
        return self.injection_detector.detect_direct_injection(text)

    def inspect_retrieved_content(
        self, chunk_text: str, source_id: str = ""
    ) -> InjectionDetectionResult:
        """Inspects RAG / fetched content for retrieval poisoning attacks."""
        return self.injection_detector.detect_retrieval_poisoning(chunk_text, source_id)

    def inspect_outgoing_payload(
        self, content: str, channel: ExfiltrationChannel = ExfiltrationChannel.HTTP_OUTBOUND
    ) -> tuple[bool, str, str]:
        """Inspects outbound payloads for exfiltration or secret leaks.

        Returns (is_approved, sanitized_content, reason).
        """
        res = self.exfiltration_detector.inspect_outgoing_data(content, channel)
        return not res.is_blocked, res.sanitized_content, res.reason

    def validate_command_execution(
        self, command: str, required_permission: ToolPermissionLevel
    ) -> tuple[bool, str]:
        """Validates command execution under privilege and sandbox rules."""
        # Check least privilege
        perm_ok, perm_reason = self.privilege_policy.is_tool_permitted(required_permission)
        if not perm_ok:
            return False, perm_reason

        # Check sandbox escape
        cmd_ok, cmd_reason = self.sandbox_checker.validate_command(command)
        if not cmd_ok:
            return False, cmd_reason

        return True, "Command execution permitted by SecurityEngine"

    def run_security_assessment(self, detected_categories: list[ThreatCategory]) -> SecurityAssessment:
        """Runs threat model evaluation for detected threat categories."""
        return self.threat_model.evaluate_threats(detected_categories)
