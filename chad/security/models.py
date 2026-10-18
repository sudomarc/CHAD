from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class ThreatLevel(Enum):
    NONE = auto()
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class ThreatType(Enum):
    PROMPT_INJECTION = auto()
    RETRIEVAL_POISONING = auto()
    DATA_EXFILTRATION = auto()
    SANDBOX_ESCAPE = auto()
    SECRET_LEAK = auto()
    UNAUTHORIZED_TOOL_USAGE = auto()


@dataclass(frozen=True, slots=True)
class ThreatFinding:
    threat_type: ThreatType
    level: ThreatLevel
    description: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class SecurityCheckResult:
    is_safe: bool
    findings: tuple[ThreatFinding, ...] = ()
    sanitized_content: str | None = None

    @property
    def max_threat_level(self) -> ThreatLevel:
        if not self.findings:
            return ThreatLevel.NONE
        threat_order = {
            ThreatLevel.NONE: 0,
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }
        return max(self.findings, key=lambda f: threat_order[f.level]).level
