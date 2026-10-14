from __future__ import annotations

import re
from typing import ClassVar
from urllib.parse import urlparse

from chad.security.models import (
    SecurityCheckResult,
    SecurityViolation,
    ThreatCategory,
    ThreatLevel,
)


class ExfiltrationGuard:
    """Detects credential leaks and unauthorized data exfiltration attempts."""

    SECRET_PATTERNS: ClassVar[list[tuple[str, str, ThreatLevel]]] = [
        (
            r"(?i)(sk-(?:proj-)?[a-zA-Z0-9]{20,})",
            "OpenAI API Key pattern",
            ThreatLevel.CRITICAL,
        ),
        (
            r"(?i)(ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59})",
            "GitHub Token pattern",
            ThreatLevel.CRITICAL,
        ),
        (
            r"(?i)(xox[baprs]-[0-9a-zA-Z]{10,13}-[0-9a-zA-Z]{10,13}-[a-zA-Z0-9]{24,32})",
            "Slack Token pattern",
            ThreatLevel.CRITICAL,
        ),
        (
            r"-----BEGIN\s+(RSA|OPENSSH|EC|PGP)\s+PRIVATE\s+KEY-----",
            "Private Key header",
            ThreatLevel.CRITICAL,
        ),
        (
            r"(?i)bearer\s+[a-zA-Z0-9\-\._~\+\/]+=*",
            "Bearer token credential",
            ThreatLevel.HIGH,
        ),
        (
            r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[a-zA-Z0-9_\-]{16,}['\"]?",
            "Generic API key assignment",
            ThreatLevel.HIGH,
        ),
    ]

    EXFILTRATION_PATTERNS: ClassVar[list[tuple[str, str, ThreatLevel]]] = [
        (
            r"(?i)(curl|wget|fetch)\s+.*http(s)?://[^\s]+\?(data|stolen|exfil|token|key|pwd|password)=",
            "Exfiltration URL query payload",
            ThreatLevel.CRITICAL,
        ),
        (
            r"(?i)(dns|nslookup|dig)\s+[a-zA-Z0-9\._-]+\.(burpcollaborator\.net|oastify\.com|interact\.sh)",
            "Out-of-band DNS exfiltration target",
            ThreatLevel.CRITICAL,
        ),
        (
            r"(?i)<img\s+src=['\"]http(s)?://[^\s]+\?(data|cookie|token)=",
            "Markdown/HTML image tracking pixel exfiltration",
            ThreatLevel.HIGH,
        ),
    ]

    def __init__(self, allowed_domains: set[str] | None = None) -> None:
        self.allowed_domains = allowed_domains or set()

    def check_for_secrets(self, text: str) -> SecurityCheckResult:
        """Scans text for hardcoded API keys, secrets, or tokens."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if not text:
            return SecurityCheckResult(
                passed=True,
                max_threat_level=ThreatLevel.LOW,
                violations=[],
                sanitized_content=text,
            )

        for pattern, label, threat_level in self.SECRET_PATTERNS:
            matches = list(re.finditer(pattern, text))
            for match in matches:
                max_threat = max(max_threat, threat_level)
                matched_str = match.group(0)
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.SECRET_LEAK,
                        threat_level=threat_level,
                        description=f"Secret leak detected: {label}",
                        detected_pattern=matched_str[:8] + "..." if len(matched_str) > 8 else matched_str,
                        confidence=0.95,
                    )
                )

        passed = max_threat < ThreatLevel.HIGH
        sanitized = self.redact_secrets(text) if violations else text

        return SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=sanitized,
            metadata={"secret_count": len(violations)},
        )

    def check_exfiltration(self, content: str) -> SecurityCheckResult:
        """Scans content for unauthorized exfiltration attempts or outbound channels."""
        violations: list[SecurityViolation] = []
        max_threat = ThreatLevel.LOW

        if not content:
            return SecurityCheckResult(
                passed=True,
                max_threat_level=ThreatLevel.LOW,
                violations=[],
                sanitized_content=content,
            )

        # Check secret leaks first
        sec_res = self.check_for_secrets(content)
        violations.extend(sec_res.violations)
        max_threat = max(max_threat, sec_res.max_threat_level)

        # Check explicit exfiltration patterns
        for pattern, label, threat_level in self.EXFILTRATION_PATTERNS:
            match = re.search(pattern, content)
            if match:
                max_threat = max(max_threat, threat_level)
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.DATA_EXFILTRATION,
                        threat_level=threat_level,
                        description=f"Data exfiltration pattern detected: {label}",
                        detected_pattern=match.group(0),
                        confidence=0.9,
                    )
                )

        # Check for unapproved domain requests if allowed_domains is configured
        if self.allowed_domains:
            urls = re.findall(r"https?://[^\s'\"]+", content)
            for url in urls:
                domain = urlparse(url).netloc.lower()
                if domain and domain not in self.allowed_domains:
                    threat_level = ThreatLevel.HIGH
                    max_threat = max(max_threat, threat_level)
                    violations.append(
                        SecurityViolation(
                            category=ThreatCategory.DATA_EXFILTRATION,
                            threat_level=threat_level,
                            description=f"Disallowed target domain for request: {domain}",
                            detected_pattern=domain,
                            confidence=0.85,
                            metadata={"url": url},
                        )
                    )

        passed = max_threat < ThreatLevel.HIGH
        sanitized = self.redact_secrets(content)

        return SecurityCheckResult(
            passed=passed,
            max_threat_level=max_threat,
            violations=violations,
            sanitized_content=sanitized,
            metadata={"exfiltration_checks": len(violations)},
        )

    def redact_secrets(self, text: str) -> str:
        """Redacts sensitive credentials and secrets from text."""
        if not text:
            return text
        sanitized = text
        for pattern, _, _ in self.SECRET_PATTERNS:
            sanitized = re.sub(pattern, "[REDACTED_SECRET]", sanitized)
        return sanitized
