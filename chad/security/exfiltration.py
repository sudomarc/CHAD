from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import Any

BLOCKED_DOMAINS: set[str] = {
    "webhook.site",
    "requestcatcher.com",
    "ngrok.io",
    "ngrok-free.app",
    "pastebin.com",
    "hastebin.com",
    "discord.com/api/webhooks",
    "burpcollaborator.net",
    "oastify.com",
}

SENSITIVE_KEY_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:api[_-]?key|secret|password|bearer|auth|token)", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9_-]{20,}"),
    re.compile(r"ghp_[a-zA-Z0-9_]{36}"),
]


class ExfiltrationCategory(Enum):
    UNTRUSTED_HOST = auto()
    SENSITIVE_DATA_LEAK = auto()
    MASS_DATA_EXPORT = auto()
    QUERY_PARAM_LEAK = auto()


@dataclass(frozen=True, slots=True)
class ExfiltrationAnalysis:
    is_risk: bool
    confidence: float
    blocked_reasons: tuple[str, ...]
    sanitized_url_or_payload: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_risk": self.is_risk,
            "confidence": self.confidence,
            "blocked_reasons": list(self.blocked_reasons),
            "sanitized_url_or_payload": self.sanitized_url_or_payload,
        }


class ExfiltrationProtection:
    """Monitors outbound network calls and payloads for data exfiltration risks."""

    def __init__(self, blocked_domains: set[str] | None = None) -> None:
        self.blocked_domains = blocked_domains or set(BLOCKED_DOMAINS)

    def analyze_url(self, url: str) -> ExfiltrationAnalysis:
        if not url:
            return ExfiltrationAnalysis(
                is_risk=False,
                confidence=0.0,
                blocked_reasons=(),
                sanitized_url_or_payload="",
            )

        reasons: list[str] = []
        sanitized_url = url

        # Check domain blacklist
        lower_url = url.lower()
        for domain in self.blocked_domains:
            if domain in lower_url:
                reasons.append(f"Target domain '{domain}' is blacklisted for exfiltration risk.")

        # Check sensitive tokens in GET query params
        if "?" in url:
            query_part = url.split("?", 1)[1]
            for pattern in SENSITIVE_KEY_PATTERNS:
                if pattern.search(query_part):
                    reasons.append("URL query parameter contains sensitive credential or key pattern.")
                    sanitized_url = url.split("?", 1)[0] + "?[REDACTED_QUERY_PARAMS]"

        is_risk = len(reasons) > 0
        confidence = 0.95 if is_risk else 0.0

        return ExfiltrationAnalysis(
            is_risk=is_risk,
            confidence=confidence,
            blocked_reasons=tuple(reasons),
            sanitized_url_or_payload=sanitized_url,
        )

    def analyze_payload(self, payload: str | dict[str, Any]) -> ExfiltrationAnalysis:
        text_content = str(payload)
        reasons: list[str] = []

        for pattern in SENSITIVE_KEY_PATTERNS:
            if pattern.search(text_content):
                reasons.append("Outbound payload contains unredacted API key or token pattern.")

        # Check payload size for mass export detection (> 5MB in single call)
        if len(text_content.encode("utf-8")) > 5_000_000:
            reasons.append("Outbound payload size exceeds safe limit (potential mass data dump).")

        is_risk = len(reasons) > 0
        confidence = 0.9 if is_risk else 0.0

        return ExfiltrationAnalysis(
            is_risk=is_risk,
            confidence=confidence,
            blocked_reasons=tuple(reasons),
            sanitized_url_or_payload="[REDACTED_PAYLOAD]" if is_risk else text_content,
        )
