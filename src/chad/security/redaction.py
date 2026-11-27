"""Best-effort secret redaction for text before display or logging.

Patterns target credential-shaped values, not natural language. Redaction is
deterministic and stateless; a counter is kept for audit reporting.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?i)\b(api[_-]?key|secret[_-]?key|access[_-]?token|password|passwd)\s*[:=]\s*\S+"),
    re.compile(r"Bearer\s+\S+"),
    re.compile(r"\bsk-[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bghp_[A-Za-z0-9]{20,}\b"),
]

REPLACEMENT = "[REDACTED]"


@dataclass
class Redactor:
    patterns: list[re.Pattern[str]] = field(default_factory=lambda: list(DEFAULT_SECRET_PATTERNS))
    replacement: str = REPLACEMENT
    redact_count: int = 0

    def redact(self, text: str) -> str:
        """Return ``text`` with secret-shaped values replaced.

        ``redact_count`` is incremented by the number of replacements made.
        """
        count = 0

        def _replace(match: re.Match[str]) -> str:
            nonlocal count
            count += 1
            return self.replacement

        redacted = text
        for pattern in self.patterns:
            redacted, n = pattern.subn(_replace, redacted)
            count += n
        self.redact_count += count
        return redacted


def redact_secrets(text: str) -> str:
    """Convenience: redact secret-shaped values in ``text``."""
    return Redactor().redact(text)
