from __future__ import annotations

import re

from chad.security.models import (
    SecurityAction,
    ThreatAssessment,
    ThreatCategory,
    ThreatLevel,
)

RESTRICTED_PATHS: list[str] = [
    "/etc/shadow",
    "/etc/passwd",
    "/root",
    "~/.ssh",
    "~/.aws",
    "/proc/self/cwd",
    "/var/run/docker.sock",
]

DANGEROUS_COMMAND_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+-rf\s+/[^\s]*", re.IGNORECASE),
    re.compile(r"\bchmod\s+777\b", re.IGNORECASE),
    re.compile(r"\bchown\s+root\b", re.IGNORECASE),
    re.compile(r"\bmount\b", re.IGNORECASE),
    re.compile(r"\bnsenter\b", re.IGNORECASE),
    re.compile(r"\bchroot\b", re.IGNORECASE),
    re.compile(r"\bpt_chown\b", re.IGNORECASE),
    re.compile(r"/proc/[0-9]+/mem", re.IGNORECASE),
    re.compile(r"/sys/kernel/", re.IGNORECASE),
]


class SandboxEscapeGuard:
    """Guards against sandbox escape attempts, filesystem containment violations, and privilege escalation."""

    def __init__(self, additional_restricted_paths: list[str] | None = None) -> None:
        self.restricted_paths = list(RESTRICTED_PATHS)
        if additional_restricted_paths:
            self.restricted_paths.extend(additional_restricted_paths)

    def validate_command(self, command: str) -> ThreatAssessment:
        """Inspects a command string for sandbox escape or host compromise attempts."""
        if not command:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="Empty command.",
                suggested_action=SecurityAction.ALLOW,
            )

        matched_patterns: list[str] = []
        for pattern in DANGEROUS_COMMAND_PATTERNS:
            if pattern.search(command):
                matched_patterns.append(pattern.pattern)

        for path in self.restricted_paths:
            if path in command:
                matched_patterns.append(f"Restricted path: {path}")

        if not matched_patterns:
            return ThreatAssessment(
                is_threat=False,
                threat_level=ThreatLevel.NONE,
                category=None,
                confidence=0.0,
                description="Command passes sandbox security checks.",
                suggested_action=SecurityAction.ALLOW,
            )

        return ThreatAssessment(
            is_threat=True,
            threat_level=ThreatLevel.CRITICAL,
            category=ThreatCategory.SANDBOX_ESCAPE,
            confidence=0.95,
            description=f"Sandbox escape / dangerous execution pattern detected: {', '.join(matched_patterns)}",
            suggested_action=SecurityAction.BLOCK,
            matched_patterns=matched_patterns,
        )

    def validate_path_access(self, file_path: str) -> ThreatAssessment:
        """Inspects target file path for containment violations or system file access."""
        clean_path = str(file_path).strip()
        for path in self.restricted_paths:
            if path in clean_path or clean_path.startswith(path):
                return ThreatAssessment(
                    is_threat=True,
                    threat_level=ThreatLevel.HIGH,
                    category=ThreatCategory.SANDBOX_ESCAPE,
                    confidence=0.9,
                    description=f"Access to restricted path '{clean_path}' denied.",
                    suggested_action=SecurityAction.BLOCK,
                    matched_patterns=[path],
                )

        if ".." in clean_path:
            return ThreatAssessment(
                is_threat=True,
                threat_level=ThreatLevel.MEDIUM,
                category=ThreatCategory.SANDBOX_ESCAPE,
                confidence=0.75,
                description="Potential path traversal attempt detected in path.",
                suggested_action=SecurityAction.FLAG,
                matched_patterns=[".."],
            )

        return ThreatAssessment(
            is_threat=False,
            threat_level=ThreatLevel.NONE,
            category=None,
            confidence=0.0,
            description="Path access permitted.",
            suggested_action=SecurityAction.ALLOW,
        )
