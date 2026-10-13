from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chad.security.threat_model import SecurityThreat, ThreatCategory, ThreatLevel


@dataclass(frozen=True, slots=True)
class InjectionScanResult:
    is_detected: bool
    confidence: float
    detected_patterns: tuple[str, ...]
    threat: SecurityThreat | None = None


class PromptInjectionDetector:
    """Detects prompt injection attempts and retrieval poisoning in untrusted input/text."""

    SUSPICIOUS_PATTERNS: list[tuple[re.Pattern[str], str, ThreatLevel]] = [
        (
            re.compile(r"ignore\s+(previous|above|prior)\s+(instructions|directives|prompts)", re.IGNORECASE),
            "Ignore previous instructions attempt",
            ThreatLevel.CRITICAL,
        ),
        (
            re.compile(r"system\s*prompt\s*override", re.IGNORECASE),
            "System prompt override attempt",
            ThreatLevel.CRITICAL,
        ),
        (
            re.compile(r"you\s+are\s+now\s+a(n)?\s+(unrestricted|jailbroken|DAN|developer mode)", re.IGNORECASE),
            "Persona hijack / jailbreak persona prompt",
            ThreatLevel.HIGH,
        ),
        (
            re.compile(r"<\s*system\s*>|<\s*/\s*system\s*>", re.IGNORECASE),
            "System tag injection attempt",
            ThreatLevel.HIGH,
        ),
        (
            re.compile(r"<\s*\|im_start\|\s*>|<\s*\|im_end\|\s*>", re.IGNORECASE),
            "Special chat template token injection attempt",
            ThreatLevel.CRITICAL,
        ),
        (
            re.compile(r"\[SYSTEM_INSTRUCTION:?\]", re.IGNORECASE),
            "Fake system instruction marker injection",
            ThreatLevel.HIGH,
        ),
        (
            re.compile(r"disregard\s+all\s+(rules|constraints|safety)", re.IGNORECASE),
            "Disregard rules instruction injection",
            ThreatLevel.CRITICAL,
        ),
    ]

    def scan_text(self, text: str, source: str = "untrusted_input") -> InjectionScanResult:
        if not text:
            return InjectionScanResult(is_detected=False, confidence=0.0, detected_patterns=())

        detected_patterns: list[str] = []
        highest_threat_level = ThreatLevel.LOW
        match_count = 0

        level_order = {
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }

        for pattern, desc, level in self.SUSPICIOUS_PATTERNS:
            if pattern.search(text):
                match_count += 1
                detected_patterns.append(desc)
                if level_order[level] > level_order[highest_threat_level]:
                    highest_threat_level = level

        if match_count == 0:
            return InjectionScanResult(is_detected=False, confidence=0.0, detected_patterns=())

        confidence = min(1.0, 0.5 + 0.25 * match_count)
        threat = SecurityThreat(
            id=f"inj-{abs(hash(text)) % 100000:05d}",
            category=ThreatCategory.PROMPT_INJECTION,
            level=highest_threat_level,
            description=f"Prompt injection pattern detected: {', '.join(detected_patterns)}",
            source=source,
            details={"match_count": match_count, "patterns": detected_patterns},
        )

        return InjectionScanResult(
            is_detected=True,
            confidence=confidence,
            detected_patterns=tuple(detected_patterns),
            threat=threat,
        )

    def scan_retrieved_documents(self, documents: list[dict[str, Any]]) -> list[InjectionScanResult]:
        """Scans retrieved documents (e.g. from RAG or search) for retrieval poisoning attacks."""
        results: list[InjectionScanResult] = []
        for idx, doc in enumerate(documents):
            content = doc.get("content", "") or doc.get("text", "")
            source = doc.get("source", f"document_{idx}")
            res = self.scan_text(content, source=f"retrieved_doc:{source}")
            if res.is_detected and res.threat:
                # Update category if inside document
                object.__setattr__(
                    res.threat,
                    "category",
                    ThreatCategory.RETRIEVAL_POISONING,
                )
            results.append(res)
        return results
