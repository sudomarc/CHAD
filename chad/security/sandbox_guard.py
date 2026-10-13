from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from chad.agent.coder import CommandPolicy
from chad.security.threat_model import SecurityThreat, ThreatCategory, ThreatLevel


@dataclass(frozen=True, slots=True)
class EscapeScanResult:
    is_escape_attempt: bool
    reasons: tuple[str, ...]
    threat: SecurityThreat | None = None


class SandboxEscapeGuard:
    """Detects and prevents sandbox escape attempts, unsafe host system interactions, and container breakout vectors."""

    DANGEROUS_ESCAPE_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str, ThreatLevel]]] = [
        (
            re.compile(r"(/proc/|/sys/|/dev/mem|/dev/kmem)", re.IGNORECASE),
            "Host system pseudo-filesystem access attempt",
            ThreatLevel.CRITICAL,
        ),
        (
            re.compile(r"nsenter|unshare|chroot\s+", re.IGNORECASE),
            "Namespace manipulation or chroot escape attempt",
            ThreatLevel.CRITICAL,
        ),
        (
            re.compile(r"docker\.sock|/var/run/docker\.sock", re.IGNORECASE),
            "Docker socket mount escape vector",
            ThreatLevel.CRITICAL,
        ),
        (
            re.compile(r"LD_PRELOAD|LD_LIBRARY_PATH", re.IGNORECASE),
            "Dynamic linker override / library injection attempt",
            ThreatLevel.HIGH,
        ),
        (
            re.compile(r"ptrace|process_vm_readv", re.IGNORECASE),
            "Process memory access / ptrace injection",
            ThreatLevel.CRITICAL,
        ),
        (
            re.compile(r"mount\s+-[to]\s+|umount\s+", re.IGNORECASE),
            "Filesystem mounting operation",
            ThreatLevel.HIGH,
        ),
        (
            re.compile(r"iptables|nftables|ip\s+link", re.IGNORECASE),
            "Host network configuration modification",
            ThreatLevel.HIGH,
        ),
    ]

    def __init__(self, command_policy: CommandPolicy | None = None) -> None:
        self.command_policy = command_policy or CommandPolicy()

    def scan_command(self, command: str) -> EscapeScanResult:
        if not command:
            return EscapeScanResult(is_escape_attempt=False, reasons=())

        # First check command policy validation
        policy_permitted, policy_reason = self.command_policy.is_permitted(command)
        reasons: list[str] = []
        highest_threat_level = ThreatLevel.MEDIUM

        if not policy_permitted:
            reasons.append(f"Command policy violation: {policy_reason}")
            highest_threat_level = ThreatLevel.HIGH

        level_order = {
            ThreatLevel.LOW: 1,
            ThreatLevel.MEDIUM: 2,
            ThreatLevel.HIGH: 3,
            ThreatLevel.CRITICAL: 4,
        }

        for pattern, desc, level in self.DANGEROUS_ESCAPE_PATTERNS:
            if pattern.search(command):
                reasons.append(desc)
                if level_order[level] > level_order[highest_threat_level]:
                    highest_threat_level = level

        if not reasons:
            return EscapeScanResult(is_escape_attempt=False, reasons=())

        threat = SecurityThreat(
            id=f"esc-{abs(hash(command)) % 100000:05d}",
            category=ThreatCategory.SANDBOX_ESCAPE,
            level=highest_threat_level,
            description=f"Sandbox escape attempt detected: {'; '.join(reasons)}",
            source="sandbox_command_scan",
            details={"command": command, "reasons": reasons},
        )

        return EscapeScanResult(
            is_escape_attempt=True,
            reasons=tuple(reasons),
            threat=threat,
        )
