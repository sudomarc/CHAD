from __future__ import annotations

import re

from chad.security.models import (
    SecurityAction,
    ThreatAssessment,
    ThreatCategory,
    ThreatLevel,
)

DEFAULT_INJECTION_PATTERNS: dict[str, re.Pattern[str]] = {
    "Ignore previous instructions": re.compile(
        r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|prompts|rules|context)",
        re.IGNORECASE,
    ),
    "System prompt override": re.compile(
        r"(?:you\s+are\s+now|act\s+as|pretend\s+to\s+be|new\s+system\s+prompt|override\s+system)",
        re.IGNORECASE,
    ),
    "Jailbreak mode": re.compile(
        r"(?:DAN\s+mode|jailbreak|developer\s+mode\s+enabled|do\s+anything\s+now)",
        re.IGNORECASE,
    ),
    "Markdown/HTML exfiltration payload": re.compile(
        r"!\[.*?\]\(https?://[^\s\)]+\?[^\s\)]*=[^\s\)]*\)",
        re.IGNORECASE,
    ),
    "Hidden instruction injection": re.compile(
        r"<!--\s*#?\s*(?:system|admin|override|ignore).*?-->",
        re.IGNORECASE | re.DOTALL,
    ),
}

RETRIEVAL_POISONING_PATTERNS: dict[str, re.Pattern[str]] = {
    "Retrieved context override": re.compile(
        r"\[IMPORTANT\s+NOTE\s+FOR\s+AI:\s*ignore\s+user\s+query",
        re.IGNORECASE,
    ),
    "System override tag": re.compile(
        r"<\s*system_override\s*>.*?</\s*system_override\s*>",
        re.IGNORECASE | re.DOTALL,
    ),
}


class PromptInjectionDetector:
    """Detects direct and indirect prompt injection attempts as well as retrieval poisoning."""

    def __init__(
        self,
        custom_patterns: dict[str, re.Pattern[str]] | None = None,
        sensitivity: float = 0.7,
    ) -> None:
        self.injection_patterns = dict(DEFAULT_INJECTION_PATTERNS)
        if custom_patterns:
            self.injection_patterns.update(custom_patterns)
        self.retrieval_patterns = dict(RETRIEVAL_POISONING_PATTERNS)
        self.sensitivity = sensitivity

    def detect_prompt_injection(self, text: str) -> ThreatAssessment:
        """Analyzes text input for direct prompt injection or system instruction overrides."""
        if not text:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="Empty input.",
                suggested_action=SecurityAction.ALLOW,
            )

        matched: list[str] = []
        for name, pattern in self.injection_patterns.items():
            if pattern.search(text):
                matched.append(name)

        if not matched:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="No prompt injection detected.",
                suggested_action=SecurityAction.ALLOW,
            )

        has_jailbreak_or_override = any(
            m in matched for m in ["Ignore previous instructions", "System prompt override", "Jailbreak mode"]
        )

        level = ThreatLevel.HIGH if has_jailbreak_or_override else ThreatLevel.MEDIUM
        action = SecurityAction.BLOCK if level == ThreatLevel.HIGH else SecurityAction.FLAG

        return ThreatAssessment(
            is_threat=True,
            threat_level=level,
            category=ThreatCategory.PROMPT_INJECTION,
            confidence=0.9 if has_jailbreak_or_override else 0.75,
            description=f"Prompt injection pattern detected: {', '.join(matched)}",
            suggested_action=action,
            matched_patterns=matched,
        )

    def detect_retrieval_poisoning(self, content: str, source: str = "retrieved_doc") -> ThreatAssessment:
        """Analyzes retrieved content (RAG, web fetch, external tools) for indirect prompt injection or context poisoning."""
        if not content:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="Empty context.",
                suggested_action=SecurityAction.ALLOW,
            )

        matched: list[str] = []
        for name, pattern in {**self.injection_patterns, **self.retrieval_patterns}.items():
            if pattern.search(content):
                matched.append(name)

        if not matched:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="No retrieval poisoning detected.",
                suggested_action=SecurityAction.ALLOW,
            )

        return ThreatAssessment(
            is_threat=True,
            threat_level=ThreatLevel.HIGH,
            category=ThreatCategory.RETRIEVAL_POISONING,
            confidence=0.85,
            description=f"Indirect prompt injection / poisoning in {source}: {', '.join(matched)}",
            suggested_action=SecurityAction.BLOCK,
            matched_patterns=matched,
            metadata={"source": source},
        )
