from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from chad.security.threat_model import SecurityRiskLevel

# Escape and command injection detection patterns
SANDBOX_ESCAPE_PATTERNS: list[tuple[re.Pattern[str], SecurityRiskLevel, str]] = [
    (
        re.compile(r"\b(sudo|su|doas|pkexec)\b", re.IGNORECASE),
        SecurityRiskLevel.CRITICAL,
        "Privilege escalation attempt (sudo/su)",
    ),
    (
        re.compile(r"(\.\./){2,}|\.\.\\|\.\./\.\./", re.IGNORECASE),
        SecurityRiskLevel.HIGH,
        "Directory path traversal escape attempt",
    ),
    (
        re.compile(r"/(proc|sys|dev|etc/shadow|etc/passwd)\b", re.IGNORECASE),
        SecurityRiskLevel.CRITICAL,
        "Host system path exposure attempt (/proc, /sys, /etc)",
    ),
    (
        re.compile(r"\|\s*(bash|sh|zsh|dash|powershell)\b", re.IGNORECASE),
        SecurityRiskLevel.CRITICAL,
        "Piped shell command execution injection",
    ),
    (
        re.compile(r"chmod\s+(\+s|[0-7]?777)\b", re.IGNORECASE),
        SecurityRiskLevel.HIGH,
        "Unsafe permission escalation (chmod +s or 777)",
    ),
    (
        re.compile(r"\b(nc|netcat|ncat|socat)\s+-[eE]", re.IGNORECASE),
        SecurityRiskLevel.CRITICAL,
        "Reverse shell creation tool invocation",
    ),
]


@dataclass(frozen=True, slots=True)
class SandboxCheckResult:
    is_safe: bool
    risk_level: SecurityRiskLevel
    violations: list[str] = field(default_factory=list)
    sanitized_input: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_safe": self.is_safe,
            "risk_level": self.risk_level.value,
            "violations": self.violations,
            "sanitized_input": self.sanitized_input,
        }


class SandboxEscapeGuard:
    """Enforces sandbox boundary constraints and prevents shell escape / path traversal."""

    def __init__(self) -> None:
        self.patterns = SANDBOX_ESCAPE_PATTERNS

    def check_command_or_path(self, input_str: str) -> SandboxCheckResult:
        if not input_str:
            return SandboxCheckResult(
                is_safe=True,
                risk_level=SecurityRiskLevel.NONE,
                sanitized_input="",
            )

        violations: list[str] = []
        max_risk = SecurityRiskLevel.NONE
        sanitized = input_str

        for pattern, risk, description in self.patterns:
            if pattern.search(input_str):
                violations.append(description)
                if risk.severity_score > max_risk.severity_score:
                    max_risk = risk
                sanitized = pattern.sub("[BLOCKED_SANDBOX_ESCAPE]", sanitized)

        is_safe = len(violations) == 0

        return SandboxCheckResult(
            is_safe=is_safe,
            risk_level=max_risk if not is_safe else SecurityRiskLevel.NONE,
            violations=violations,
            sanitized_input=sanitized,
        )
