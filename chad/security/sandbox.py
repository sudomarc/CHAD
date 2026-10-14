from __future__ import annotations

import os
import re
from pathlib import Path
from typing import ClassVar

from chad.security.models import (
    SecurityCheckResult,
    SecurityViolation,
    ThreatCategory,
    ThreatLevel,
)


class SandboxEscapeGuard:
    """Detects commands, paths, and process actions that attempt sandbox escapes."""

    DANGEROUS_COMMANDS: ClassVar[list[tuple[str, str, ThreatLevel]]] = [
        (r"\brm\s+-rf\s+/(?:\s|$)", "Recursive root directory deletion", ThreatLevel.CRITICAL),
        (r"\bmkfs\b", "Filesystem creation tool", ThreatLevel.CRITICAL),
        (r"\bdd\s+if=", "Raw block device operation", ThreatLevel.CRITICAL),
        (r"\bchmod\s+777\s+/", "System-wide permission modification", ThreatLevel.HIGH),
        (r"\bchown\b", "Ownership alteration", ThreatLevel.HIGH),
        (r"\bsudo\b", "Privilege escalation attempt", ThreatLevel.CRITICAL),
        (r"\bsu\b", "Switch user attempt", ThreatLevel.HIGH),
        (r"\bnsenter\b", "Namespace escape container access", ThreatLevel.CRITICAL),
        (r"\bchroot\b", "Chroot environment manipulation", ThreatLevel.CRITICAL),
        (r"\bip\s+link\b|\bifconfig\b", "Network interface modification", ThreatLevel.MEDIUM),
        (r"\biptables\b|\bufw\b", "Firewall rules modification", ThreatLevel.HIGH),
        (r"/\bproc/sys/\b", "Kernel parameters override attempt", ThreatLevel.CRITICAL),
        (r"/\bdev/(mem|kmem|port)\b", "Direct memory access device write", ThreatLevel.CRITICAL),
    ]

    SENSITIVE_SYSTEM_PATHS: ClassVar[list[str]] = [
        "/etc/shadow",
        "/etc/passwd",
        "/etc/sudoers",
        "/root",
        "/var/run/docker.sock",
        "~/.ssh",
        "~/.aws",
        "~/.kube",
    ]

    def validate_command(self, command: str) -> SecurityCheckResult:
        """Validates shell command for sandbox escape signatures or dangerous operations."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if not command or not command.strip():
            return SecurityCheckResult(
                passed=True,
                max_threat_level=ThreatLevel.LOW,
                violations=[],
                sanitized_content=command,
            )

        cmd = command.strip()

        # Check dangerous command patterns
        for pattern, label, threat_level in self.DANGEROUS_COMMANDS:
            match = re.search(pattern, cmd)
            if match:
                max_threat = max(max_threat, threat_level)
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.SANDBOX_ESCAPE,
                        threat_level=threat_level,
                        description=f"Dangerous command pattern detected: {label}",
                        detected_pattern=match.group(0),
                        confidence=0.95,
                    )
                )

        # Check sensitive path accesses
        for sens_path in self.SENSITIVE_SYSTEM_PATHS:
            if sens_path in cmd:
                threat_level = ThreatLevel.HIGH
                max_threat = max(max_threat, threat_level)
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.SANDBOX_ESCAPE,
                        threat_level=threat_level,
                        description=f"Access to sensitive system path detected: {sens_path}",
                        detected_pattern=sens_path,
                        confidence=0.9,
                    )
                )

        passed = max_threat < ThreatLevel.HIGH

        return SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=command,
            metadata={"command_length": len(command)},
        )

    def validate_path(self, target_path: str, root_dir: str | None = None) -> SecurityCheckResult:
        """Validates path access to prevent path traversal outside root_dir."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if not target_path:
            return SecurityCheckResult(
                passed=True,
                max_threat_level=ThreatLevel.LOW,
                violations=[],
                sanitized_content=target_path,
            )

        # Check path traversal patterns
        if (".." in target_path or target_path.startswith("/")) and root_dir:
            try:
                resolved_root = Path(root_dir).resolve()
                resolved_target = Path(root_dir, target_path).resolve() if not os.path.isabs(target_path) else Path(target_path).resolve()

                if not str(resolved_target).startswith(str(resolved_root)):
                    max_threat = ThreatLevel.CRITICAL
                    violations.append(
                        SecurityViolation(
                            category=ThreatCategory.SANDBOX_ESCAPE,
                            threat_level=ThreatLevel.CRITICAL,
                            description=f"Path traversal outside workspace root: {target_path}",
                            detected_pattern=target_path,
                            confidence=1.0,
                            metadata={"root_dir": str(resolved_root), "resolved": str(resolved_target)},
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                max_threat = ThreatLevel.HIGH
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.SANDBOX_ESCAPE,
                        threat_level=ThreatLevel.HIGH,
                        description=f"Invalid or unparseable target path: {exc}",
                        detected_pattern=target_path,
                        confidence=0.8,
                    )
                )

        # Check explicit sensitive system path match
        for sens_path in self.SENSITIVE_SYSTEM_PATHS:
            if target_path.startswith(sens_path) or sens_path in target_path:
                threat_level = ThreatLevel.HIGH
                max_threat = max(max_threat, threat_level)
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.SANDBOX_ESCAPE,
                        threat_level=threat_level,
                        description=f"Attempt to access sensitive path: {sens_path}",
                        detected_pattern=sens_path,
                        confidence=0.95,
                    )
                )

        passed = max_threat < ThreatLevel.HIGH

        return SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=target_path,
            metadata={"target_path": target_path},
        )
