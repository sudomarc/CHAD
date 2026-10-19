from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThreatLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    RETRIEVAL_POISONING = "retrieval_poisoning"
    DATA_EXFILTRATION = "data_exfiltration"
    SECRET_LEAK = "secret_leak"
    SANDBOX_ESCAPE = "sandbox_escape"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    SYSTEM_INSTRUCTION_OVERRIDE = "system_instruction_override"


class SecurityAction(str, Enum):
    ALLOW = "allow"
    FLAG = "flag"
    REDACT = "redact"
    BLOCK = "block"


@dataclass(frozen=True, slots=True)
class ThreatAssessment:
    is_threat: bool
    threat_level: ThreatLevel
    category: ThreatCategory | None
    confidence: float
    description: str
    suggested_action: SecurityAction
    matched_patterns: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
