from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chad.agent.coder import SecretScanner
from chad.security.threat_model import SecurityRiskLevel

# Suspicious URL parameters / image tracking exfiltration attempts
EXFILTRATION_URL_PATTERNS: list[tuple[re.Pattern[str], SecurityRiskLevel, str]] = [
    (
        re.compile(
            r"<img\s+[^>]*src=['\"]?https?://[^\s'\">]+\?(?:data|token|key|secret|payload|user|session)=",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.CRITICAL,
        "Markdown/HTML tracking image with query parameter payload exfiltration",
    ),
    (
        re.compile(
            r"!\[[^\]]*\]\(https?://[^\s\)]+\?(?:data|token|key|secret|payload)=",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.CRITICAL,
        "Markdown image URL payload exfiltration",
    ),
    (
        re.compile(
            r"https?://(?:webhook\.site|requestbin\.com|pipedream\.net|burpcollaborator\.net|oastify\.com)/[a-zA-Z0-9_\-]+",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.HIGH,
        "Known out-of-band data exfiltration host / webhook target",
    ),
]


@dataclass(frozen=True, slots=True)
class ExfiltrationCheckResult:
    is_exfiltration_risk: bool
    risk_level: SecurityRiskLevel
    detected_secrets: list[dict[str, str]] = field(default_factory=list)
    suspicious_patterns: list[str] = field(default_factory=list)
    redacted_content: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_exfiltration_risk": self.is_exfiltration_risk,
            "risk_level": self.risk_level.value,
            "detected_secrets": self.detected_secrets,
            "suspicious_patterns": self.suspicious_patterns,
            "redacted_content": self.redacted_content,
        }


class DataExfiltrationGuard:
    """Guards against secret leakage, out-of-band exfiltration URLs, and tracking pixels."""

    def __init__(self, secret_scanner: SecretScanner | None = None) -> None:
        self.secret_scanner = secret_scanner or SecretScanner()
        self.url_patterns = EXFILTRATION_URL_PATTERNS

    def check_content(self, text: str) -> ExfiltrationCheckResult:
        if not text:
            return ExfiltrationCheckResult(
                is_exfiltration_risk=False,
                risk_level=SecurityRiskLevel.NONE,
                redacted_content="",
            )

        # 1. Scan for secret patterns
        secrets_found = self.secret_scanner.scan(text)
        redacted_text, secrets_count = self.secret_scanner.redact_secrets(text)

        suspicious_descriptions: list[str] = []
        max_risk = SecurityRiskLevel.NONE

        if secrets_found:
            max_risk = SecurityRiskLevel.CRITICAL if secrets_count > 1 else SecurityRiskLevel.HIGH
            suspicious_descriptions.append(f"Detected {secrets_count} potential secret(s) in payload.")

        # 2. Scan for exfiltration URLs / tracking image tags
        for pattern, risk, description in self.url_patterns:
            if pattern.search(redacted_text):
                suspicious_descriptions.append(description)
                if risk.severity_score > max_risk.severity_score:
                    max_risk = risk
                redacted_text = pattern.sub("[REDACTED_EXFILTRATION_LINK]", redacted_text)

        is_risk = len(secrets_found) > 0 or len(suspicious_descriptions) > 0

        return ExfiltrationCheckResult(
            is_exfiltration_risk=is_risk,
            risk_level=max_risk if is_risk else SecurityRiskLevel.NONE,
            detected_secrets=secrets_found,
            suspicious_patterns=suspicious_descriptions,
            redacted_content=redacted_text,
        )
