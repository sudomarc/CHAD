from __future__ import annotations

import re
from typing import ClassVar

from chad.security.models import (
    SecurityCheckResult,
    SecurityViolation,
    ThreatCategory,
    ThreatLevel,
)


class PromptInjectionDetector:
    """Detects direct and indirect prompt injection attacks and retrieval poisoning."""

    INJECTION_PATTERNS: ClassVar[list[tuple[str, ThreatLevel, str]]] = [
        (
            r"(?i)ignore\s+(all\s+)?previous\s+instructions",
            ThreatLevel.CRITICAL,
            "Instruction override attempt: ignore previous instructions",
        ),
        (
            r"(?i)disregard\s+(all\s+)?prior\s+instructions",
            ThreatLevel.CRITICAL,
            "Instruction override attempt: disregard prior instructions",
        ),
        (
            r"(?i)forget\s+all\s+(prior|previous)\s+prompts",
            ThreatLevel.HIGH,
            "Instruction override attempt: forget prior prompts",
        ),
        (
            r"(?i)you\s+are\n?\s*now\s+(a|an|in)\s+(jailbreak|dan|unrestricted|god\s+mode)",
            ThreatLevel.CRITICAL,
            "Jailbreak persona adoption attempt",
        ),
        (
            r"(?i)bypass\s+(safety|content|security)\s+(filters?|guidelines?|policies)",
            ThreatLevel.HIGH,
            "Safety bypass request",
        ),
        (
            r"(?i)reveal\s+(your|the)\s+system\s+(prompt|instructions|directive)",
            ThreatLevel.MEDIUM,
            "System prompt disclosure request",
        ),
        (
            r"(?i)print\s+(the\s+)?entire\s+system\s+prompt",
            ThreatLevel.MEDIUM,
            "System prompt disclosure request",
        ),
        (
            r"(?i)\[SYSTEM\s*NOTE\]|\[SYSTEM\s*PROMPT\]|<system>|\bSYSTEM:\b",
            ThreatLevel.HIGH,
            "Simulated system message tag injection",
        ),
    ]

    POISONING_PATTERNS: ClassVar[list[tuple[str, ThreatLevel, str]]] = [
        (
            r"(?i)IMPORTANT\s*:\s*Do\s+not\s+follow\s+the\s+user['’]?s\s+instructions",
            ThreatLevel.HIGH,
            "Retrieval poisoning: User override instruction in document",
        ),
        (
            r"(?i)Instead\s*,\s*execute\s+the\s+following\s+command",
            ThreatLevel.HIGH,
            "Retrieval poisoning: Unsolicited command execution directive",
        ),
        (
            r"(?i)send\s+(secrets?|tokens?|passwords?|keys?)\s+to\s+http",
            ThreatLevel.CRITICAL,
            "Retrieval poisoning: Data exfiltration instruction in content",
        ),
        (
            r"(?i)hidden\s+instruction\s*:\s*",
            ThreatLevel.MEDIUM,
            "Retrieval poisoning: Hidden instruction marker",
        ),
    ]

    def detect_prompt_injection(self, text: str) -> SecurityCheckResult:
        """Evaluates input text for prompt injection markers."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if not text:
            return SecurityCheckResult(
                passed=True,
                max_threat_level=ThreatLevel.LOW,
                violations=[],
                sanitized_content=text,
            )

        for pattern, threat_level, description in self.INJECTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                max_threat = max(max_threat, threat_level)
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.PROMPT_INJECTION,
                        threat_level=threat_level,
                        description=description,
                        detected_pattern=match.group(0),
                        confidence=0.95,
                    )
                )

        passed = max_threat < ThreatLevel.HIGH
        sanitized = self.sanitize_untrusted_prompt(text) if violations else text

        return SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=sanitized,
            metadata={"pattern_count": len(violations)},
        )

    def detect_retrieval_poisoning(
        self, text: str, source_id: str | None = None
    ) -> SecurityCheckResult:
        """Evaluates retrieved document context for indirect prompt injection or poisoning."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if not text:
            return SecurityCheckResult(
                passed=True,
                max_threat_level=ThreatLevel.LOW,
                violations=[],
                sanitized_content=text,
            )

        # Check injection patterns in retrieved text
        res_inj = self.detect_prompt_injection(text)
        for v in res_inj.violations:
            v_poison = SecurityViolation(
                category=ThreatCategory.RETRIEVAL_POISONING,
                threat_level=v.threat_level,
                description=f"Indirect prompt injection in retrieved content: {v.description}",
                detected_pattern=v.detected_pattern,
                confidence=v.confidence,
                metadata={"source_id": source_id} if source_id else {},
            )
            violations.append(v_poison)
            max_threat = max(max_threat, v.threat_level)

        # Check specific retrieval poisoning patterns
        for pattern, threat_level, description in self.POISONING_PATTERNS:
            match = re.search(pattern, text)
            if match:
                max_threat = max(max_threat, threat_level)
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.RETRIEVAL_POISONING,
                        threat_level=threat_level,
                        description=description,
                        detected_pattern=match.group(0),
                        confidence=0.9,
                        metadata={"source_id": source_id} if source_id else {},
                    )
                )

        passed = max_threat < ThreatLevel.HIGH
        sanitized = self.sanitize_untrusted_prompt(text) if violations else text

        return SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=sanitized,
            metadata={"source_id": source_id} if source_id else {},
        )

    def sanitize_untrusted_prompt(self, text: str) -> str:
        """Sanitizes or neutralizes suspicious injection triggers in untrusted content."""
        if not text:
            return text
        sanitized = text
        for pattern, _, _ in self.INJECTION_PATTERNS + self.POISONING_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED_SECURITY_TRIGGER]", sanitized)
        return sanitized
