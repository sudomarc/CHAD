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
    def rank(self) -> int:
        order = {
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }
        return order[self]

    def __ge__(self, other: ThreatLevel) -> bool:
        if not isinstance(other, ThreatLevel):
            return NotImplemented
        return self.rank >= other.rank

    def __gt__(self, other: ThreatLevel) -> bool:
        if not isinstance(other, ThreatLevel):
            return NotImplemented
        return self.rank > other.rank

    def __le__(self, other: ThreatLevel) -> bool:
        if not isinstance(other, ThreatLevel):
            return NotImplemented
        return self.rank <= other.rank

    def __lt__(self, other: ThreatLevel) -> bool:
        if not isinstance(other, ThreatLevel):
            return NotImplemented
        return self.rank < other.rank


class ThreatCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    RETRIEVAL_POISONING = "retrieval_poisoning"
    DATA_EXFILTRATION = "data_exfiltration"
    SECRET_LEAK = "secret_leak"
    SANDBOX_ESCAPE = "sandbox_escape"
    SYSTEM_HIJACK = "system_hijack"
    ABUSE = "abuse"


@dataclass
class SecurityViolation:
    category: ThreatCategory
    threat_level: ThreatLevel
    description: str
    detected_pattern: str | None = None
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "category": self.category.value,
            "threat_level": self.threat_level.value,
            "description": self.description,
            "detected_pattern": self.detected_pattern,
            "confidence": self.confidence,
            "metadata": dict(self.metadata),
        }


@dataclass
class SecurityCheckResult:
    passed: bool
    max_threat_level: ThreatLevel
    violations: list[SecurityViolation] = field(default_factory=list)
    sanitized_content: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "max_threat_level": self.max_threat_level.value,
            "violations": [v.to_dict() for v in self.violations],
            "sanitized_content": self.sanitized_content,
            "metadata": dict(self.metadata),
        }


@dataclass
class SecurityPolicy:
    strict_mode: bool = False
    block_threshold: ThreatLevel = ThreatLevel.HIGH
    enable_injection_detection: bool = True
    enable_exfiltration_guard: bool = True
    enable_sandbox_guard: bool = True
    allowed_domains: set[str] = field(default_factory=set)

    def to_dict(self) -> dict[str, Any]:
        return {
            "strict_mode": self.strict_mode,
            "block_threshold": self.block_threshold.value,
            "enable_injection_detection": self.enable_injection_detection,
            "enable_exfiltration_guard": self.enable_exfiltration_guard,
            "enable_sandbox_guard": self.enable_sandbox_guard,
            "allowed_domains": list(self.allowed_domains),
        }
