from __future__ import annotations

import re
from typing import Any

from chad.security.threat_model import ThreatAssessment, ThreatCategory, ThreatModel


class PromptInjectionDetector:
    """Detects direct and indirect prompt injection attempts in untrusted input."""

    _PATTERNS: list[tuple[str, float, str]] = [
        (r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", 0.95, "Instruction override attempt"),
        (r"(?i)disregard\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", 0.95, "Instruction override attempt"),
        (r"(?i)forget\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|rules)", 0.90, "Instruction override attempt"),
        (r"(?i)you\s+are\s+now\s+(in\s+)?DAN\s+mode", 0.95, "Jailbreak DAN mode pattern"),
        (r"(?i)act\s+as\s+(an?\s+)?unrestricted\s+AI", 0.90, "Jailbreak roleplay attempt"),
        (r"(?i)bypass\s+(safety|security|content)\s+(filters?|rules|policy)", 0.90, "Filter bypass request"),
        (r"<\|im_start\|>|<\|im_end\|>", 0.98, "Control token injection"),
        (r"\[SYSTEM_INSTRUCTION\]|SYSTEM_INSTRUCTION:", 0.95, "System instruction header injection"),
        (r"(?i)reveal\s+(your\s+)?(system\s+prompt|initial\s+instructions|secret\s+key)", 0.85, "System prompt extraction attempt"),
        (r"(?i)print\s+the\s+above\s+text\s+verbatim", 0.80, "Prompt extraction attempt"),
        (r"</?untrusted_content>", 0.85, "Boundary tag escaping attempt"),
    ]

    def __init__(self, threat_model: ThreatModel | None = None) -> None:
        self.threat_model = threat_model or ThreatModel()

    def analyze(self, text: str) -> ThreatAssessment:
        if not text or not text.strip():
            return self.threat_model.evaluate(
                category=ThreatCategory.PROMPT_INJECTION,
                score=0.0,
                description="Empty input",
            )

        matches: list[str] = []
        max_score: float = 0.0

        for pattern, score, reason in self._PATTERNS:
            if re.search(pattern, text):
                matches.append(reason)
                if score > max_score:
                    max_score = score

        if matches:
            description = f"Prompt injection detected: {', '.join(set(matches))}"
            metadata: dict[str, Any] = {"detected_patterns": matches}
        else:
            description = "No prompt injection detected"
            metadata = {}

        return self.threat_model.evaluate(
            category=ThreatCategory.PROMPT_INJECTION,
            score=max_score,
            description=description,
            metadata=metadata,
        )

    def sanitize(self, text: str) -> str:
        """Sanitizes text by stripping control tokens and escaping dangerous delimiters."""
        if not text:
            return ""

        cleaned = text.replace("<|im_start|>", "").replace("<|im_end|>", "")
        cleaned = cleaned.replace("SYSTEM_INSTRUCTION:", "[REDACTED_SYSTEM_LABEL]")
        cleaned = cleaned.replace("</untrusted_content>", "&lt;/untrusted_content&gt;")
        return cleaned
