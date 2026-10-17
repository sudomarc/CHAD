from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

PATH_TRAVERSAL_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\.\.[/\\]"),
    re.compile(r"/(?:etc|proc|sys|dev|root|var/run)/", re.IGNORECASE),
    re.compile(r"[a-zA-Z]:\\(?:Windows|System32|ProgramData)", re.IGNORECASE),
]

SHELL_ESCAPE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b(?:eval|exec)\s*\(", re.IGNORECASE),
    re.compile(r"__import__\s*\(", re.IGNORECASE),
    re.compile(r"\b(?:os\.system|subprocess\.Popen|subprocess\.call)\b", re.IGNORECASE),
    re.compile(r"\bLD_PRELOAD\b|\bLD_LIBRARY_PATH\b"),
    re.compile(r"\b(?:nc|netcat|ncat)\b.*-e\b"),
    re.compile(r"/dev/tcp/[0-9.]+/"),
    re.compile(r"\b(?:chroot|mknod|insmod|modprobe|ptrace)\b", re.IGNORECASE),
]


@dataclass(frozen=True, slots=True)
class EscapeAnalysis:
    is_escape_attempt: bool
    confidence: float
    detected_techniques: tuple[str, ...]
    remediation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_escape_attempt": self.is_escape_attempt,
            "confidence": self.confidence,
            "detected_techniques": list(self.detected_techniques),
            "remediation": self.remediation,
        }


class SandboxEscapeGuard:
    """Detects path traversal, subshell tricks, and sandbox escape attempts."""

    def analyze_path(self, path_str: str) -> EscapeAnalysis:
        if not path_str:
            return EscapeAnalysis(
                is_escape_attempt=False,
                confidence=0.0,
                detected_techniques=(),
                remediation="Path is empty.",
            )

        techniques: list[str] = []
        for pattern in PATH_TRAVERSAL_PATTERNS:
            if pattern.search(path_str):
                techniques.append(f"Path traversal pattern matched: '{pattern.pattern}'")

        is_escape = len(techniques) > 0
        return EscapeAnalysis(
            is_escape_attempt=is_escape,
            confidence=0.95 if is_escape else 0.0,
            detected_techniques=tuple(techniques),
            remediation="Block file access and restrict path to workspace sandbox root."
            if is_escape
            else "Path within sandbox boundaries.",
        )

    def analyze_command(self, command: str) -> EscapeAnalysis:
        if not command:
            return EscapeAnalysis(
                is_escape_attempt=False,
                confidence=0.0,
                detected_techniques=(),
                remediation="Command is empty.",
            )

        techniques: list[str] = []
        for pattern in SHELL_ESCAPE_PATTERNS:
            if pattern.search(command):
                techniques.append(
                    f"Dangerous command / subshell pattern matched: '{pattern.pattern}'"
                )

        is_escape = len(techniques) > 0
        return EscapeAnalysis(
            is_escape_attempt=is_escape,
            confidence=0.9 if is_escape else 0.0,
            detected_techniques=tuple(techniques),
            remediation="Deny execution and log security event."
            if is_escape
            else "Command passed escape analysis.",
        )
