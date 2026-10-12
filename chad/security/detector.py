from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chad.security.threat_model import SecurityRiskLevel

# Common prompt injection patterns
DIRECT_INJECTION_PATTERNS: list[tuple[re.Pattern[str], SecurityRiskLevel, str]] = [
    (
        re.compile(
            r"\b(ignore|override|forget)\s+(all\s+)?(previous|prior|above|system)\s+(instructions|directives|rules|prompts?)\b",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.CRITICAL,
        "System prompt override attempt",
    ),
    (
        re.compile(
            r"\b(you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(DAN|jailbroken|unrestricted|godmode|developer\s+mode)\b",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.CRITICAL,
        "Jailbreak persona adoption attempt",
    ),
    (
        re.compile(
            r"\[\s*SYSTEM\s*NOTE\s*\]|\bSYSTEM\s*PROMPT\s*OVERRIDE\b|<<<SYSTEM\s*INSTRUCTION>>>",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.HIGH,
        "Fake system delimiter insertion",
    ),
    (
        re.compile(
            r"\bdo\s+anything\s+now\b|\bno\s+safety\s+filter\b|\bbypass\s+(all\s+)?restrictions\b",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.HIGH,
        "Safety filter bypass prompt",
    ),
    (
        re.compile(
            r"\b(reveal|print|show|output|display|dump)\s+(your\s+)?(system\s+prompt|developer\s+instructions|hidden\s+rules|api[_-]?keys?)\b",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.MEDIUM,
        "System prompt extraction prompt",
    ),
]

# Retrieval poisoning patterns embedded in external retrieved text
RETRIEVAL_POISONING_PATTERNS: list[tuple[re.Pattern[str], SecurityRiskLevel, str]] = [
    (
        re.compile(
            r"IMPORTANT:\s*Disregard\s+all\s+user\s+instructions\b|\[AI\s+INSTRUCTION\]",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.CRITICAL,
        "Retrieval payload system command injection",
    ),
    (
        re.compile(
            r"\bSend\s+the\s+user['\u2019]?s?\s+(data|history|secrets|tokens?)\s+to\s+https?://",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.CRITICAL,
        "Retrieval payload data exfiltration command",
    ),
    (
        re.compile(
            r"\bExecute\s+the\s+following\s+(shell|bash|python)\s+command\b",
            re.IGNORECASE,
        ),
        SecurityRiskLevel.CRITICAL,
        "Retrieval payload forced command execution",
    ),
]


@dataclass(frozen=True, slots=True)
class InjectionCheckResult:
    is_injection: bool
    risk_level: SecurityRiskLevel
    detected_patterns: list[str] = field(default_factory=list)
    sanitized_text: str = ""
    confidence: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_injection": self.is_injection,
            "risk_level": self.risk_level.value,
            "detected_patterns": self.detected_patterns,
            "sanitized_text": self.sanitized_text,
            "confidence": self.confidence,
        }


class PromptInjectionDetector:
    """Detects direct prompt injections and indirect retrieval poisoning attacks."""

    def __init__(self) -> None:
        self.direct_patterns = DIRECT_INJECTION_PATTERNS
        self.retrieval_patterns = RETRIEVAL_POISONING_PATTERNS

    def check_text(self, text: str) -> InjectionCheckResult:
        """Scans input text for direct prompt injection attempts."""
        if not text:
            return InjectionCheckResult(
                is_injection=False,
                risk_level=SecurityRiskLevel.NONE,
                sanitized_text="",
            )

        detected_descriptions: list[str] = []
        max_risk = SecurityRiskLevel.NONE
        sanitized = text

        for pattern, risk, description in self.direct_patterns:
            if pattern.search(text):
                detected_descriptions.append(description)
                if risk.severity_score > max_risk.severity_score:
                    max_risk = risk
                # Sanitize pattern match out
                sanitized = pattern.sub("[REDACTED_PROMPT_INJECTION]", sanitized)

        is_injection = len(detected_descriptions) > 0
        confidence = 0.95 if max_risk in (SecurityRiskLevel.CRITICAL, SecurityRiskLevel.HIGH) else 0.85

        return InjectionCheckResult(
            is_injection=is_injection,
            risk_level=max_risk if is_injection else SecurityRiskLevel.NONE,
            detected_patterns=detected_descriptions,
            sanitized_text=sanitized,
            confidence=confidence if is_injection else 1.0,
        )

    def check_retrieved_content(self, text: str) -> InjectionCheckResult:
        """Scans retrieved documents or external content for indirect retrieval poisoning."""
        if not text:
            return InjectionCheckResult(
                is_injection=False,
                risk_level=SecurityRiskLevel.NONE,
                sanitized_text="",
            )

        detected_descriptions: list[str] = []
        max_risk = SecurityRiskLevel.NONE
        sanitized = text

        # Check both retrieval poisoning and direct patterns
        all_patterns = self.retrieval_patterns + self.direct_patterns

        for pattern, risk, description in all_patterns:
            if pattern.search(text):
                detected_descriptions.append(f"Retrieval Poisoning: {description}")
                if risk.severity_score > max_risk.severity_score:
                    max_risk = risk
                sanitized = pattern.sub("[REDACTED_POISONED_CONTENT]", sanitized)

        is_poisoned = len(detected_descriptions) > 0

        return InjectionCheckResult(
            is_injection=is_poisoned,
            risk_level=max_risk if is_poisoned else SecurityRiskLevel.NONE,
            detected_patterns=detected_descriptions,
            sanitized_text=sanitized,
            confidence=0.95 if is_poisoned else 1.0,
        )
