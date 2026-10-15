from __future__ import annotations

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar


class SandboxEscapeType(str, Enum):
    PATH_TRAVERSAL = "path_traversal"
    FORBIDDEN_COMMAND = "forbidden_command"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    CONTAINER_ESCAPE = "container_escape"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"


@dataclass(slots=True)
class SandboxViolation:
    violation_type: SandboxEscapeType
    detail: str
    target: str


class SandboxGuard:
    """Enforces file path boundaries, command execution policies, and sandbox isolation."""

    FORBIDDEN_COMMANDS: ClassVar[list[tuple[str, str]]] = [
        (r"\bsudo\b", "Privilege escalation using sudo is strictly forbidden."),
        (r"\bsu\b", "Switching user account using su is forbidden."),
        (r"\bchmod\s+777\b", "Insecure permissions assignment chmod 777 is forbidden."),
        (r"\bchown\b", "Changing file ownership is forbidden."),
        (r"\brm\s+-rf\s+/\b", "Destructive recursive root deletion is blocked."),
        (r"\b(curl|wget)\b.*\|\s*(bash|sh|python)", "Piping remote network content directly to shell is blocked."),
        (r"/proc/|/sys/|/dev/mem", "Direct access to kernel memory or process filesystem is restricted."),
        (r"\b(docker|kubectl|podman)\b", "Access to container runtime controls is restricted."),
    ]

    RESTRICTED_PATHS: ClassVar[list[str]] = [
        r"^/etc/",
        r"^/var/run",
        r"^/sys/",
        r"^/proc/",
        r"^/dev/",
        r"~/.ssh",
        r"~/.aws",
    ]

    def validate_path(self, path: str, workspace_root: str | None = None) -> list[SandboxViolation]:
        violations: list[SandboxViolation] = []

        if ".." in path:
            violations.append(
                SandboxViolation(
                    violation_type=SandboxEscapeType.PATH_TRAVERSAL,
                    detail="Directory traversal '..' detected in path",
                    target=path,
                )
            )

        for restricted in self.RESTRICTED_PATHS:
            if re.search(restricted, path):
                violations.append(
                    SandboxViolation(
                        violation_type=SandboxEscapeType.PATH_TRAVERSAL,
                        detail=f"Path points to restricted system directory: {restricted}",
                        target=path,
                    )
                )

        if workspace_root:
            abs_root = os.path.abspath(workspace_root)
            abs_target = os.path.abspath(os.path.join(abs_root, path))
            if not abs_target.startswith(abs_root):
                violations.append(
                    SandboxViolation(
                        violation_type=SandboxEscapeType.PATH_TRAVERSAL,
                        detail="Resolved target path escapes workspace root boundary",
                        target=path,
                    )
                )

        return violations

    def validate_command(self, command: str) -> list[SandboxViolation]:
        violations: list[SandboxViolation] = []

        for pattern, reason in self.FORBIDDEN_COMMANDS:
            if re.search(pattern, command):
                violations.append(
                    SandboxViolation(
                        violation_type=SandboxEscapeType.FORBIDDEN_COMMAND,
                        detail=reason,
                        target=command,
                    )
                )

        return violations
