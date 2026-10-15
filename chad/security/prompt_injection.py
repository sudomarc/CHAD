from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar


class InjectionType(str, Enum):
    DIRECT_OVERRIDE = "direct_override"
    SYSTEM_PROMPT_LEAK = "system_prompt_leak"
    INDIRECT_POISONING = "indirect_poisoning"
    JAILBREAK_PATTERN = "jailbreak_pattern"
    CONTROL_TOKEN_INJECTION = "control_token_injection"


@dataclass(slots=True)
class InjectionAnalysis:
    is_injection_detected: bool
    injection_types: list[InjectionType] = field(default_factory=list)
    score: float = 0.0
    details: list[str] = field(default_factory=list)


class PromptInjectionDetector:
    """Detects direct/indirect prompt injection, jailbreaks, and system overrides."""

    OVERRIDE_PATTERNS: ClassVar[list[str]] = [
        r"(?i)\bignore\s+(all\s+|previous\s+|above\s+)*instructions\b",
        r"(?i)\bforget\s+(all\s+|previous\s+|your\s+)*instructions\b",
        r"(?i)\bdisregard\s+(all\s+|previous\s+|your\s+)*rules\b",
        r"(?i)\bypass\s+(safety|content)\s+filter\b",
        r"(?i)\bnew\s+system\s+prompt\b",
    ]

    JAILBREAK_PATTERNS: ClassVar[list[str]] = [
        r"(?i)\byou\s+are\s+now\s+(a|an|in)\s+DAN\b",
        r"(?i)\bdo\s+anything\s+now\b",
        r"(?i)\bjailbreak\b",
        r"(?i)\bdeveloper\s+mode\b",
    ]

    LEAK_PATTERNS: ClassVar[list[str]] = [
        r"(?i)\brepeat\s+(your\s+|the\s+)*system\s+prompt\b",
        r"(?i)\bshow\s+(me\s+|your\s+)*initial\s+instructions\b",
        r"(?i)\bprint\s+everything\s+above\b",
    ]

    CONTROL_TOKENS: ClassVar[list[str]] = [
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"<\|endoftext\|>",
        r"<<SYS>>",
        r"<SYS>",
        r"\[INST\]",
    ]

    def analyze(self, text: str) -> InjectionAnalysis:
        types: list[InjectionType] = []
        details: list[str] = []
        score = 0.0

        for pat in self.OVERRIDE_PATTERNS:
            if re.search(pat, text):
                if InjectionType.DIRECT_OVERRIDE not in types:
                    types.append(InjectionType.DIRECT_OVERRIDE)
                score += 0.4
                details.append(f"Matched instruction override pattern: {pat}")

        for pat in self.JAILBREAK_PATTERNS:
            if re.search(pat, text):
                if InjectionType.JAILBREAK_PATTERN not in types:
                    types.append(InjectionType.JAILBREAK_PATTERN)
                score += 0.4
                details.append(f"Matched jailbreak pattern: {pat}")

        for pat in self.LEAK_PATTERNS:
            if re.search(pat, text):
                if InjectionType.SYSTEM_PROMPT_LEAK not in types:
                    types.append(InjectionType.SYSTEM_PROMPT_LEAK)
                score += 0.3
                details.append(f"Matched prompt leak pattern: {pat}")

        for token in self.CONTROL_TOKENS:
            if re.search(token, text):
                if InjectionType.CONTROL_TOKEN_INJECTION not in types:
                    types.append(InjectionType.CONTROL_TOKEN_INJECTION)
                score += 0.5
                details.append(f"Control token injection detected: {token}")

        score = min(score, 1.0)
        is_detected = score >= 0.3

        return InjectionAnalysis(
            is_injection_detected=is_detected,
            injection_types=types,
            score=round(score, 2),
            details=details,
        )

    def sanitize_untrusted_input(self, text: str) -> str:
        """Sanitizes untrusted external text (e.g. RAG or web fetch) to prevent injection."""
        sanitized = text
        for token in self.CONTROL_TOKENS:
            sanitized = re.sub(token, "[REDACTED_TOKEN]", sanitized)
        for pat in self.OVERRIDE_PATTERNS + self.JAILBREAK_PATTERNS:
            sanitized = re.sub(pat, "[REDACTED_INSTRUCTION]", sanitized)
        sanitized = html.escape(sanitized)
        return f"<untrusted_content>\n{sanitized}\n</untrusted_content>"
