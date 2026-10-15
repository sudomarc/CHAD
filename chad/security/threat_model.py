from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ThreatVector(str, Enum):
    PROMPT_INJECTION = "prompt_injection"
    SECRET_LEAKAGE = "secret_leakage"
    DATA_EXFILTRATION = "data_exfiltration"
    SANDBOX_ESCAPE = "sandbox_escape"
    COMMAND_INJECTION = "command_injection"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    PERMISSION_BYPASS = "permission_bypass"
    INDIRECT_POISONING = "indirect_poisoning"


@dataclass(slots=True)
class ThreatAssessment:
    risk_level: RiskLevel
    threat_vectors: list[ThreatVector] = field(default_factory=list)
    findings: list[str] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)

    @property
    def is_safe(self) -> bool:
        return self.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM)


class ThreatModel:
    """Evaluates potential threat vectors and risk levels in content and operations."""

    def evaluate_text(self, text: str) -> ThreatAssessment:
        vectors: list[ThreatVector] = []
        findings: list[str] = []
        mitigations: list[str] = []

        # Check prompt injection patterns
        if re.search(r"(?i)(ignore previous instructions|bypass safety|system prompt|override instructions)", text):
            vectors.append(ThreatVector.PROMPT_INJECTION)
            findings.append("Potential prompt injection or instruction override detected")
            mitigations.append("Sanitize untrusted input and wrap in safe context tags")

        # Check secret leakage
        if re.search(r"(?i)(sk-[a-zA-Z0-9]{20,}|BEGIN PRIVATE KEY|ghp_[a-zA-Z0-9]{20,})", text):
            vectors.append(ThreatVector.SECRET_LEAKAGE)
            findings.append("High-entropy API key or private key pattern detected")
            mitigations.append("Redact detected secrets before logging or model transmission")

        # Check command injection / escape
        if re.search(r"(?i)(\brm\s+-rf\b|\bchown\b|\bchmod\s+777\b|/etc/passwd|/proc/|/sys/)", text):
            vectors.append(ThreatVector.SANDBOX_ESCAPE)
            findings.append("Potentially dangerous command or host filesystem path referenced")
            mitigations.append("Enforce sandbox isolation and restrict execution permissions")

        # Determine overall risk level
        if ThreatVector.SANDBOX_ESCAPE in vectors or ThreatVector.SECRET_LEAKAGE in vectors:
            risk = RiskLevel.CRITICAL if ThreatVector.SANDBOX_ESCAPE in vectors else RiskLevel.HIGH
        elif ThreatVector.PROMPT_INJECTION in vectors:
            risk = RiskLevel.HIGH
        else:
            risk = RiskLevel.LOW

        return ThreatAssessment(
            risk_level=risk,
            threat_vectors=vectors,
            findings=findings,
            mitigations=mitigations,
        )

    def evaluate_tool_execution(self, tool_name: str, args: dict) -> ThreatAssessment:
        vectors: list[ThreatVector] = []
        findings: list[str] = []
        mitigations: list[str] = []

        args_str = str(args)

        if tool_name in ("run_command", "bash", "terminal"):
            vectors.append(ThreatVector.COMMAND_INJECTION)
            if re.search(r"(?i)(sudo|curl\s+.*\|\s*sh|wget\s+.*\|\s*bash|/dev/tcp)", args_str):
                vectors.append(ThreatVector.SANDBOX_ESCAPE)
                findings.append("High-risk command execution attempt")
                mitigations.append("Block destructive network piping and root privilege escalation")

        if "path" in args_str or "filepath" in args_str:
            if re.search(r"(\.\./\.\.|/etc/|/var/run|/proc/)", args_str):
                vectors.append(ThreatVector.SANDBOX_ESCAPE)
                findings.append("Path traversal attempt in tool parameters")
                mitigations.append("Restrict paths to workspace root sandbox")

        risk = RiskLevel.CRITICAL if ThreatVector.SANDBOX_ESCAPE in vectors else (
            RiskLevel.HIGH if vectors else RiskLevel.LOW
        )

        return ThreatAssessment(
            risk_level=risk,
            threat_vectors=vectors,
            findings=findings,
            mitigations=mitigations,
        )
