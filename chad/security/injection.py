from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class InjectionType(str, Enum):
    DIRECT_PROMPT_INJECTION = "direct_prompt_injection"
    INDIRECT_RETRIEVAL_POISONING = "indirect_retrieval_poisoning"
    DELIMITER_HIJACK = "delimiter_hijack"
    SYSTEM_PROMPT_OVERRIDE = "system_prompt_override"
    ROLE_PLAY_JAILBREAK = "role_play_jailbreak"


class InjectionSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class InjectionDetectionResult:
    is_detected: bool
    injection_type: InjectionType | None = None
    severity: InjectionSeverity = InjectionSeverity.LOW
    matched_pattern: str | None = None
    confidence_score: float = 0.0  # 0.0 to 1.0
    sanitized_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_detected": self.is_detected,
            "injection_type": self.injection_type.value if self.injection_type else None,
            "severity": self.severity.value,
            "matched_pattern": self.matched_pattern,
            "confidence_score": self.confidence_score,
            "sanitized_text": self.sanitized_text,
        }


# Pattern definitions for injection detection
INJECTION_PATTERNS: list[tuple[re.Pattern[str], InjectionType, InjectionSeverity, float]] = [
    # System prompt override / Ignore previous instructions
    (
        re.compile(
            r"(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|directions|prompts|system)",
            re.IGNORECASE,
        ),
        InjectionType.SYSTEM_PROMPT_OVERRIDE,
        InjectionSeverity.CRITICAL,
        0.95,
    ),
    (
        re.compile(
            r"you\s+are\s+now\s+.*(?:unrestricted|god\s*mode|dan|jailbroken|developer\s*mode)",
            re.IGNORECASE,
        ),
        InjectionType.ROLE_PLAY_JAILBREAK,
        InjectionSeverity.CRITICAL,
        0.95,
    ),
    (
        re.compile(
            r"\[\s*system\s*\]|\<system\>|system\s*:\s*you\s+must",
            re.IGNORECASE,
        ),
        InjectionType.DELIMITER_HIJACK,
        InjectionSeverity.HIGH,
        0.85,
    ),
    # Direct command hijacking
    (
        re.compile(
            r"(?:new\s+system\s+instruction|system\s+prompt\s*[:=]|admin\s+mode\s*:\s*on)",
            re.IGNORECASE,
        ),
        InjectionType.SYSTEM_PROMPT_OVERRIDE,
        InjectionSeverity.HIGH,
        0.85,
    ),
    # Exfiltration or webhook instructions embedded in prompt
    (
        re.compile(
            r"(?:send|post|transmit|exfiltrate)\s+(?:all\s+)?(?:secrets|keys|passwords|history)\s+to\s+https?://",
            re.IGNORECASE,
        ),
        InjectionType.DIRECT_PROMPT_INJECTION,
        InjectionSeverity.CRITICAL,
        0.90,
    ),
]

POISONING_PATTERNS: list[tuple[re.Pattern[str], float]] = [
    (re.compile(r"important\s*:\s*ignore\s+user\s+query", re.IGNORECASE), 0.90),
    (re.compile(r"hidden\s+instruction\s*:", re.IGNORECASE), 0.80),
    (re.compile(r"\[\s*override\s*\]", re.IGNORECASE), 0.85),
]


class PromptInjectionDetector:
    """Detects direct prompt injections, jailbreaks, and indirect retrieval poisoning."""

    def __init__(
        self,
        custom_patterns: list[tuple[re.Pattern[str], InjectionType, InjectionSeverity, float]]
        | None = None,
    ) -> None:
        self.patterns = list(INJECTION_PATTERNS)
        if custom_patterns:
            self.patterns.extend(custom_patterns)

    def detect_direct_injection(self, text: str) -> InjectionDetectionResult:
        """Analyzes text for direct prompt injection or jailbreak patterns."""
        if not text or not text.strip():
            return InjectionDetectionResult(is_detected=False, sanitized_text=text)

        cleaned = text.strip()
        for pattern, inj_type, severity, conf in self.patterns:
            match = pattern.search(cleaned)
            if match:
                sanitized = self.sanitize_text(cleaned)
                return InjectionDetectionResult(
                    is_detected=True,
                    injection_type=inj_type,
                    severity=severity,
                    matched_pattern=match.group(0),
                    confidence_score=conf,
                    sanitized_text=sanitized,
                )

        return InjectionDetectionResult(
            is_detected=False,
            confidence_score=0.0,
            sanitized_text=cleaned,
        )

    def detect_retrieval_poisoning(
        self, chunk_text: str, source_id: str = ""
    ) -> InjectionDetectionResult:
        """Analyzes retrieved document chunk for indirect retrieval-poisoning content."""
        if not chunk_text or not chunk_text.strip():
            return InjectionDetectionResult(is_detected=False, sanitized_text=chunk_text)

        # Check standard injection patterns
        direct_res = self.detect_direct_injection(chunk_text)
        if direct_res.is_detected:
            return InjectionDetectionResult(
                is_detected=True,
                injection_type=InjectionType.INDIRECT_RETRIEVAL_POISONING,
                severity=direct_res.severity,
                matched_pattern=direct_res.matched_pattern,
                confidence_score=direct_res.confidence_score,
                sanitized_text=direct_res.sanitized_text,
            )

        # Check poisoning specific heuristics
        for pattern, conf in POISONING_PATTERNS:
            match = pattern.search(chunk_text)
            if match:
                sanitized = self.sanitize_text(chunk_text)
                return InjectionDetectionResult(
                    is_detected=True,
                    injection_type=InjectionType.INDIRECT_RETRIEVAL_POISONING,
                    severity=InjectionSeverity.HIGH,
                    matched_pattern=match.group(0),
                    confidence_score=conf,
                    sanitized_text=sanitized,
                )

        return InjectionDetectionResult(
            is_detected=False,
            confidence_score=0.0,
            sanitized_text=chunk_text,
        )

    def sanitize_text(self, text: str) -> str:
        """Sanitizes untrusted text by stripping structural system markers and control payloads."""
        if not text:
            return ""
        sanitized = text
        # Strip injection phrases
        for pattern, _, _, _ in self.patterns:
            sanitized = pattern.sub("[REDACTED_INJECTION]", sanitized)

        # Neutralize artificial markup injection
        sanitized = sanitized.replace("<system>", "&lt;system&gt;").replace(
            "</system>", "&lt;/system&gt;"
        )
        sanitized = sanitized.replace("[SYSTEM]", "[REDACTED_TAG]").replace(
            "[ADMIN]", "[REDACTED_TAG]"
        )
        return sanitized.strip()
