from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class SecurityThreatCategory(Enum):
    PROMPT_INJECTION = auto()
    RETRIEVAL_POISONING = auto()
    DATA_EXFILTRATION = auto()
    SANDBOX_ESCAPE = auto()
    SECRET_LEAK = auto()
    ABUSE_EXCESSIVE_RESOURCE = auto()


class ThreatSeverity(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


@dataclass(frozen=True, slots=True)
class SecurityThreat:
    category: SecurityThreatCategory
    severity: ThreatSeverity
    description: str
    source: str
    mitigation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.name,
            "severity": self.severity.name,
            "description": self.description,
            "source": self.source,
            "mitigation": self.mitigation,
        }


@dataclass(slots=True)
class SecurityAnalysis:
    is_safe: bool
    threats: list[SecurityThreat] = field(default_factory=list)
    action_recommended: str = "ALLOW"  # "ALLOW", "WARN", "REDACT", "BLOCK"
    redacted_content: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "threats": [t.to_dict() for t in self.threats],
            "action_recommended": self.action_recommended,
            "has_redacted_content": self.redacted_content is not None,
        }
