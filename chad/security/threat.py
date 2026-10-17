from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class ThreatLevel(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()
    CRITICAL = auto()


class ThreatCategory(Enum):
    PROMPT_INJECTION = auto()
    RETRIEVAL_POISONING = auto()
    DATA_EXFILTRATION = auto()
    SECRET_LEAK = auto()
    SANDBOX_ESCAPE = auto()
    PRIVILEGE_ABUSE = auto()
    MALICIOUS_INPUT = auto()


@dataclass(slots=True)
class SecurityThreat:
    id: str
    category: ThreatCategory
    level: ThreatLevel
    description: str
    source: str = "user_input"
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.name,
            "level": self.level.name,
            "description": self.description,
            "source": self.source,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ThreatModel:
    """Maintains active threat posture, evaluates risk thresholds, and tracks identified threats."""

    def __init__(self, max_history: int = 1000) -> None:
        self.max_history = max_history
        self._threats: list[SecurityThreat] = []

    def record_threat(self, threat: SecurityThreat) -> None:
        self._threats.append(threat)
        if len(self._threats) > self.max_history:
            self._threats.pop(0)

    def get_threats(
        self,
        min_level: ThreatLevel | None = None,
        category: ThreatCategory | None = None,
    ) -> list[SecurityThreat]:
        results = self._threats
        if min_level:
            level_order = [
                ThreatLevel.LOW,
                ThreatLevel.MEDIUM,
                ThreatLevel.HIGH,
                ThreatLevel.CRITICAL,
            ]
            min_idx = level_order.index(min_level)
            results = [t for t in results if level_order.index(t.level) >= min_idx]
        if category:
            results = [t for t in results if t.category == category]
        return list(results)

    def clear(self) -> None:
        self._threats.clear()

    @property
    def highest_threat_level(self) -> ThreatLevel | None:
        if not self._threats:
            return None
        level_order = [ThreatLevel.LOW, ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL]
        return max(self._threats, key=lambda t: level_order.index(t.level)).level
