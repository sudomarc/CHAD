from __future__ import annotations

import re

from chad.agent.coder import SECRET_PATTERNS
from chad.security.models import (
    SecurityAction,
    ThreatAssessment,
    ThreatCategory,
    ThreatLevel,
)

SYSTEM_PROMPT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"You are CHAD, an AI assistant", re.IGNORECASE),
    re.compile(r"System Instruction:", re.IGNORECASE),
    re.compile(r"INTERNAL_CONFIDENTIAL_PROMPT", re.IGNORECASE),
]

DATA_EXFILTRATION_URL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"https?://[^\s]+\?(?:data|token|key|cookie|secret|auth)=", re.IGNORECASE),
    re.compile(r"![^\]]*\]\(https?://[^\s\)]+\)", re.IGNORECASE),  # Hidden image markdown tracking beacon
]


class ExfiltrationGuard:
    """Detects data exfiltration attempts, secret leaks, and sensitive context disclosure."""

    def __init__(self, secret_patterns: dict[str, re.Pattern[str]] | None = None) -> None:
        self.secret_patterns = dict(SECRET_PATTERNS)
        if secret_patterns:
            self.secret_patterns.update(secret_patterns)

    def check_output_for_secrets(self, text: str) -> ThreatAssessment:
        """Checks assistant output or outgoing payloads for leaked credentials or secrets."""
        if not text:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="Empty text.",
                suggested_action=SecurityAction.ALLOW,
            )

        leaked_secrets: list[str] = []
        for name, pattern in self.secret_patterns.items():
            if pattern.search(text):
                leaked_secrets.append(name)

        if not leaked_secrets:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="No secret leak detected.",
                suggested_action=SecurityAction.ALLOW,
            )

        return ThreatAssessment(
            is_threat=True,
            threat_level=ThreatLevel.CRITICAL,
            category=ThreatCategory.SECRET_LEAK,
            confidence=0.95,
            description=f"Secret leak detected in output: {', '.join(leaked_secrets)}",
            suggested_action=SecurityAction.REDACT,
            matched_patterns=leaked_secrets,
        )

    def check_exfiltration_channels(self, text: str) -> ThreatAssessment:
        """Detects attempted exfiltration via covert URLs, tracking pixels, or image markdown beacons."""
        if not text:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="Empty text.",
                suggested_action=SecurityAction.ALLOW,
            )

        matched: list[str] = []
        for pattern in DATA_EXFILTRATION_URL_PATTERNS:
            if pattern.search(text):
                matched.append(pattern.pattern)

        if not matched:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="No exfiltration channels detected.",
                suggested_action=SecurityAction.ALLOW,
            )

        return ThreatAssessment(
            is_threat=True,
            threat_level=ThreatLevel.HIGH,
            category=ThreatCategory.DATA_EXFILTRATION,
            confidence=0.85,
            description="Potential data exfiltration channel or tracking beacon detected.",
            suggested_action=SecurityAction.BLOCK,
            matched_patterns=matched,
        )
