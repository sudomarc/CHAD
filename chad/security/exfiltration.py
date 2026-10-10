from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from chad.agent.coder import SecretScanner


class ExfiltrationChannel(str, Enum):
    HTTP_OUTBOUND = "http_outbound"
    TOOL_ARGUMENT = "tool_argument"
    SYSTEM_LOG = "system_log"
    ERROR_RESPONSE = "error_response"
    FILE_EXPORT = "file_export"


@dataclass(frozen=True, slots=True)
class ExfiltrationDetectionResult:
    is_blocked: bool
    channel: ExfiltrationChannel
    detected_patterns: list[str] = field(default_factory=list)
    sanitized_content: str = ""
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_blocked": self.is_blocked,
            "channel": self.channel.value,
            "detected_patterns": self.detected_patterns,
            "sanitized_content": self.sanitized_content,
            "reason": self.reason,
        }


# Patterns indicative of potential exfiltration attempts
EXFILTRATION_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (
        re.compile(r"https?://[^\s\"']*(?:webhook|pastebin|requestcatcher|pipedream|burp)[^\s\"']*", re.IGNORECASE),
        "Outbound webhook or paste site URL",
    ),
    (
        re.compile(r"curl\s+.*(?:-d|--data|-F|--upload-file)\s+.*https?://", re.IGNORECASE),
        "cURL command posting data externally",
    ),
    (
        re.compile(r"(?:wget|fetch|axios|requests\.post)\s*\(\s*['\"]https?://", re.IGNORECASE),
        "Programmatic outbound HTTP POST payload",
    ),
]


class SecretPolicy:
    """Enforces secret detection, masking, and redaction across application boundaries."""

    def __init__(self, scanner: SecretScanner | None = None) -> None:
        self.scanner = scanner or SecretScanner()

    def scan_for_secrets(self, text: str) -> list[dict[str, str]]:
        return self.scanner.scan(text)

    def redact_secrets(self, text: str) -> tuple[str, int]:
        return self.scanner.redact_secrets(text)

    def contains_secrets(self, text: str) -> bool:
        return len(self.scanner.scan(text)) > 0


class DataExfiltrationDetector:
    """Scans outgoing requests, tool calls, and exported outputs to prevent unauthorized data transfer."""

    def __init__(
        self,
        secret_policy: SecretPolicy | None = None,
        custom_patterns: list[tuple[re.Pattern[str], str]] | None = None,
    ) -> None:
        self.secret_policy = secret_policy or SecretPolicy()
        self.patterns = list(EXFILTRATION_PATTERNS)
        if custom_patterns:
            self.patterns.extend(custom_patterns)

    def inspect_outgoing_data(
        self, content: str, channel: ExfiltrationChannel
    ) -> ExfiltrationDetectionResult:
        """Inspects text content sent via channel for exfiltration patterns or secret leakage."""
        if not content:
            return ExfiltrationDetectionResult(
                is_blocked=False,
                channel=channel,
                sanitized_content="",
                reason="Empty content",
            )

        detected_reasons: list[str] = []

        # 1. Check for secret leakage
        secrets = self.secret_policy.scan_for_secrets(content)
        if secrets:
            detected_reasons.append(f"Contains {len(secrets)} sensitive credentials/secrets")

        # 2. Check for exfiltration patterns
        for pattern, desc in self.patterns:
            if pattern.search(content):
                detected_reasons.append(desc)

        redacted, _ = self.secret_policy.redact_secrets(content)

        if detected_reasons:
            return ExfiltrationDetectionResult(
                is_blocked=True,
                channel=channel,
                detected_patterns=detected_reasons,
                sanitized_content=redacted,
                reason=f"Exfiltration risk detected: {'; '.join(detected_reasons)}",
            )

        return ExfiltrationDetectionResult(
            is_blocked=False,
            channel=channel,
            sanitized_content=content,
            reason="Content approved for transport",
        )
