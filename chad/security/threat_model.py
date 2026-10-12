from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThreatCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    RETRIEVAL_POISONING = "retrieval_poisoning"
    DATA_EXFILTRATION = "data_exfiltration"
    SECRET_LEAKAGE = "secret_leakage"
    SANDBOX_ESCAPE = "sandbox_escape"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    UNAUTHORIZED_TOOL_USE = "unauthorized_tool_use"


class SecurityRiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    NONE = "none"

    @property
    def severity_score(self) -> int:
        scores = {
            SecurityRiskLevel.CRITICAL: 4,
            SecurityRiskLevel.HIGH: 3,
            SecurityRiskLevel.MEDIUM: 2,
            SecurityRiskLevel.LOW: 1,
            SecurityRiskLevel.NONE: 0,
        }
        return scores[self]


@dataclass(frozen=True, slots=True)
class ThreatAssessment:
    category: ThreatCategory
    risk_level: SecurityRiskLevel
    title: str
    description: str
    mitigation: str
    confidence_score: float = 1.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "risk_level": self.risk_level.value,
            "title": self.title,
            "description": self.description,
            "mitigation": self.mitigation,
            "confidence_score": self.confidence_score,
        }


@dataclass
class ThreatModel:
    """Registry and taxonomy of security threats and risk policies."""

    assessments: list[ThreatAssessment] = field(default_factory=list)

    def evaluate_max_risk(self) -> SecurityRiskLevel:
        if not self.assessments:
            return SecurityRiskLevel.NONE
        max_assessment = max(self.assessments, key=lambda a: a.risk_level.severity_score)
        return max_assessment.risk_level

    def add_threat(self, assessment: ThreatAssessment) -> None:
        self.assessments.append(assessment)

    def get_threats_by_category(self, category: ThreatCategory) -> list[ThreatAssessment]:
        return [a for a in self.assessments if a.category == category]

    def get_threats_at_or_above_level(
        self, min_risk: SecurityRiskLevel
    ) -> list[ThreatAssessment]:
        return [
            a for a in self.assessments if a.risk_level.severity_score >= min_risk.severity_score
        ]

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_risk_level": self.evaluate_max_risk().value,
            "total_threats": len(self.assessments),
            "threats": [a.to_dict() for a in self.assessments],
        }
