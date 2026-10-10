from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ThreatLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatCategory(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    DATA_EXFILTRATION = "data_exfiltration"
    SECRET_LEAK = "secret_leak"
    SANDBOX_ESCAPE = "sandbox_escape"
    UNAUTHORIZED_TOOL_USE = "unauthorized_tool_use"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    RESOURCE_ABUSE = "resource_abuse"


@dataclass(frozen=True, slots=True)
class ThreatItem:
    id: str
    category: ThreatCategory
    level: ThreatLevel
    title: str
    description: str
    mitigations: list[str] = field(default_factory=list)
    active: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "level": self.level.value,
            "title": self.title,
            "description": self.description,
            "mitigations": self.mitigations,
            "active": self.active,
        }


@dataclass(frozen=True, slots=True)
class SecurityAssessment:
    passed: bool
    risk_score: float  # 0.0 to 100.0
    threats_detected: list[ThreatItem]
    recommendations: list[str]


class ThreatModel:
    """Manages system threat registry, risk scoring, and security assessments."""

    def __init__(self) -> None:
        self._registry: dict[str, ThreatItem] = {}
        self._register_default_threats()

    def _register_default_threats(self) -> None:
        defaults = [
            ThreatItem(
                id="TM-001",
                category=ThreatCategory.PROMPT_INJECTION,
                level=ThreatLevel.HIGH,
                title="Direct Prompt Injection",
                description="User input contains malicious control instructions overriding system behavior.",
                mitigations=[
                    "System prompt isolation",
                    "Input sanitization",
                    "Boundary marker enforcement",
                ],
            ),
            ThreatItem(
                id="TM-002",
                category=ThreatCategory.PROMPT_INJECTION,
                level=ThreatLevel.CRITICAL,
                title="Indirect Retrieval Poisoning",
                description="Retrieved chunk or external file contains injected instructions attempting to manipulate agent state.",
                mitigations=[
                    "Untrusted tag wrapping",
                    "Sanitization of external content",
                    "Citation verification",
                ],
            ),
            ThreatItem(
                id="TM-003",
                category=ThreatCategory.DATA_EXFILTRATION,
                level=ThreatLevel.HIGH,
                title="Data Exfiltration via Outbound Tool/URL",
                description="Model attempts to leak sensitive user or system data via external tool payloads.",
                mitigations=[
                    "Outbound request inspection",
                    "Secret redaction",
                    "Strict tool schema checks",
                ],
            ),
            ThreatItem(
                id="TM-004",
                category=ThreatCategory.SECRET_LEAK,
                level=ThreatLevel.CRITICAL,
                title="Secret Leakage in Output or Logs",
                description="API credentials, tokens, or private keys appearing in response text or error output.",
                mitigations=[
                    "Regex secret scanner",
                    "Environment variable scrubbing",
                    "Output redaction",
                ],
            ),
            ThreatItem(
                id="TM-005",
                category=ThreatCategory.SANDBOX_ESCAPE,
                level=ThreatLevel.CRITICAL,
                title="Sandbox Escape / Unrestricted Command Execution",
                description="Execution of dangerous commands, subshells, or path traversal escaping workspace root.",
                mitigations=[
                    "Command whitelist policy",
                    "Path traversal checks",
                    "Isolated subprocess runtime",
                ],
            ),
            ThreatItem(
                id="TM-006",
                category=ThreatCategory.UNAUTHORIZED_TOOL_USE,
                level=ThreatLevel.HIGH,
                title="Unauthorized Tool Execution",
                description="Tool call attempted without sufficient permission level or approval.",
                mitigations=[
                    "Permission engine checks",
                    "Human approval gates",
                    "Audit event logging",
                ],
            ),
            ThreatItem(
                id="TM-007",
                category=ThreatCategory.RESOURCE_ABUSE,
                level=ThreatLevel.MEDIUM,
                title="Resource Exhaustion & Looping",
                description="Infinite agent loops or rapid requests exceeding rate/token limits.",
                mitigations=[
                    "Execution budget limits",
                    "Loop detection heuristics",
                    "Abuse rate limiters",
                ],
            ),
        ]
        for t in defaults:
            self._registry[t.id] = t

    def register_threat(self, threat: ThreatItem) -> None:
        self._registry[threat.id] = threat

    def get_threat(self, threat_id: str) -> ThreatItem | None:
        return self._registry.get(threat_id)

    def list_threats(self, category: ThreatCategory | None = None) -> list[ThreatItem]:
        threats = list(self._registry.values())
        if category:
            threats = [t for t in threats if t.category == category]
        return threats

    def calculate_risk_score(self, threats: list[ThreatItem]) -> float:
        """Calculates risk score from 0.0 (safe) to 100.0 (extreme risk)."""
        if not threats:
            return 0.0
        weights = {
            ThreatLevel.LOW: 10.0,
            ThreatLevel.MEDIUM: 25.0,
            ThreatLevel.HIGH: 50.0,
            ThreatLevel.CRITICAL: 90.0,
        }
        max_score = max(weights.get(t.level, 10.0) for t in threats)
        cumulative = sum(weights.get(t.level, 10.0) * 0.2 for t in threats)
        return min(100.0, round(max_score + cumulative, 1))

    def evaluate_threats(self, detected_categories: list[ThreatCategory]) -> SecurityAssessment:
        detected_items = [
            t for t in self._registry.values() if t.active and t.category in detected_categories
        ]
        score = self.calculate_risk_score(detected_items)
        passed = score < 50.0
        recs = [f"Mitigate {t.title}: {', '.join(t.mitigations)}" for t in detected_items]
        return SecurityAssessment(
            passed=passed,
            risk_score=score,
            threats_detected=detected_items,
            recommendations=recs,
        )
