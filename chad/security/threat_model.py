from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ThreatCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    RETRIEVAL_POISONING = "retrieval_poisoning"
    DATA_EXFILTRATION = "data_exfiltration"
    SECRET_LEAKAGE = "secret_leakage"
    SANDBOX_ESCAPE = "sandbox_escape"
    UNAUTHORIZED_TOOL_USE = "unauthorized_tool_use"
    RESOURCE_ABUSE = "resource_abuse"


class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class SecurityThreat:
    id: str
    category: ThreatCategory
    level: ThreatLevel
    description: str
    source: str
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "level": self.level.value,
            "description": self.description,
            "source": self.source,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


class ThreatModelEvaluator:
    """Evaluates security context and produces threat assessments based on threat scores and categories."""

    def evaluate_threat_score(self, threats: list[SecurityThreat]) -> tuple[ThreatLevel, float]:
        if not threats:
            return ThreatLevel.LOW, 0.0

        weights = {
            ThreatLevel.LOW: 1.0,
            ThreatLevel.MEDIUM: 3.0,
            ThreatLevel.HIGH: 7.0,
            ThreatLevel.CRITICAL: 10.0,
        }

        total_score = sum(weights[t.level] for t in threats)
        max_level = max(threats, key=lambda t: weights[t.level]).level

        return max_level, total_score
