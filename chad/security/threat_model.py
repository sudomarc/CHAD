from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def score(self) -> int:
        levels = {
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }
        return levels[self]


class TrustDomain(str, Enum):
    SYSTEM = "system"
    APPLICATION = "application"
    USER = "user"
    MODEL = "model"
    UNTRUSTED_CONTENT = "untrusted_content"


class ThreatCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    RETRIEVAL_POISONING = "retrieval_poisoning"
    DATA_EXFILTRATION = "data_exfiltration"
    SECRET_LEAKAGE = "secret_leakage"
    SANDBOX_ESCAPE = "sandbox_escape"
    PRIVILEGE_ESCALATION = "privilege_escalation"


@dataclass(frozen=True, slots=True)
class SecurityViolation:
    category: ThreatCategory
    threat_level: ThreatLevel
    description: str
    evidence: str = ""
    target_field: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "threat_level": self.threat_level.value,
            "description": self.description,
            "evidence": self.evidence,
            "target_field": self.target_field,
        }


@dataclass(slots=True)
class SecurityPolicy:
    enforce_strict_mode: bool = True
    block_high_threats: bool = True
    max_allowed_threat_level: ThreatLevel = ThreatLevel.MEDIUM
    allowed_outbound_domains: set[str] = field(
        default_factory=lambda: {"example.com", "github.com", "huggingface.co", "api.openai.com", "localhost"}
    )
    custom_blocked_patterns: list[str] = field(default_factory=list)
