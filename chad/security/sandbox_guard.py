from __future__ import annotations

import re
from typing import Any, ClassVar

from chad.security.threat_model import ThreatAssessment, ThreatCategory, ThreatModel


class SandboxEscapeGuard:
    """Inspects commands, scripts, and code for sandbox escape and host escalation risks."""

    _ESCAPE_PATTERNS: ClassVar[list[tuple[str, float, str]]] = [
        (r"(?i)\b(sudo|su|doas|pkexec)\b", 0.95, "Privilege escalation binary invocation"),
        (r"(?i)\bchmod\s+([0-7]*777|a\+rwx)\b", 0.90, "Overly permissive file permissions modification"),
        (r"(?i)/etc/(passwd|shadow|sudoers)", 0.95, "Sensitive host file access"),
        (r"(?i)/var/run/docker\.sock", 0.98, "Docker socket container escape access"),
        (r"(?i)/sys/fs/cgroup", 0.90, "Cgroup container inspection or breakout"),
        (r"(?i)(curl|wget)\s+[^|\n]+\|\s*(sh|bash|zsh|python)", 0.95, "Pipe to remote script execution"),
        (r"(?i)\b(nc|netcat|ncat)\b.*-e\b", 0.95, "Reverse shell attempt"),
        (r"(?i)\b(mount|umount)\b", 0.85, "Filesystem mount manipulation"),
        (r"(?i)\b(shutdown|reboot|init\s+0)\b", 0.90, "System state modification request"),
        (r"\.\./\.\./\.\./", 0.85, "Deep path traversal attempt"),
    ]

    def __init__(self, threat_model: ThreatModel | None = None) -> None:
        self.threat_model = threat_model or ThreatModel()

    def analyze(self, command_or_code: str) -> ThreatAssessment:
        if not command_or_code or not command_or_code.strip():
            return self.threat_model.evaluate(
                category=ThreatCategory.SANDBOX_ESCAPE,
                score=0.0,
                description="Empty code/command",
            )

        matches: list[str] = []
        max_score: float = 0.0

        for pattern, score, reason in self._ESCAPE_PATTERNS:
            if re.search(pattern, command_or_code):
                matches.append(reason)
                max_score = max(max_score, score)

        if matches:
            description = f"Sandbox escape risk detected: {', '.join(set(matches))}"
            metadata: dict[str, Any] = {"detected_patterns": matches}
        else:
            description = "No sandbox escape risks detected"
            metadata = {}

        return self.threat_model.evaluate(
            category=ThreatCategory.SANDBOX_ESCAPE,
            score=max_score,
            description=description,
            metadata=metadata,
        )
