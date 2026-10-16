from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThreatCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    SYSTEM_HIJACK = "system_hijack"
    DATA_EXFILTRATION = "data_exfiltration"
    SANDBOX_ESCAPE = "sandbox_escape"
    SECRET_LEAK = "secret_leak"
    PERMISSION_BYPASS = "permission_bypass"
    RESOURCE_ABUSE = "resource_abuse"


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ActionRecommendation(str, Enum):
    ALLOW = "allow"
    WARN = "warn"
    BLOCK = "block"
    QUARANTINE = "quarantine"


@dataclass(frozen=True, slots=True)
class ThreatAssessment:
    category: ThreatCategory
    risk_level: RiskLevel
    score: float
    description: str
    recommendation: ActionRecommendation
    metadata: dict[str, Any] = field(default_factory=dict)


class ThreatModel:
    """Evaluates and prioritizes security threats across application boundaries."""

    def __init__(self, high_risk_threshold: float = 0.7, critical_threshold: float = 0.9) -> None:
        self.high_risk_threshold = high_risk_threshold
        self.critical_threshold = critical_threshold

    def evaluate(
        self,
        category: ThreatCategory,
        score: float,
        description: str,
        metadata: dict[str, Any] | None = None,
    ) -> ThreatAssessment:
        score = max(0.0, min(1.0, score))
        if score >= self.critical_threshold:
            risk = RiskLevel.CRITICAL
            rec = ActionRecommendation.BLOCK
        elif score >= self.high_risk_threshold:
            risk = RiskLevel.HIGH
            rec = ActionRecommendation.BLOCK
        elif score >= 0.4:
            risk = RiskLevel.MEDIUM
            rec = ActionRecommendation.WARN
        elif score > 0.0:
            risk = RiskLevel.LOW
            rec = ActionRecommendation.ALLOW
        else:
            risk = RiskLevel.NONE
            rec = ActionRecommendation.ALLOW

        return ThreatAssessment(
            category=category,
            risk_level=risk,
            score=score,
            description=description,
            recommendation=rec,
            metadata=metadata or {},
        )
