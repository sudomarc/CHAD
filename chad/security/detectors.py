from __future__ import annotations

import re
from urllib.parse import urlparse

from chad.security.threat_model import (
    SecurityPolicy,
    SecurityViolation,
    ThreatCategory,
    ThreatLevel,
)


class PromptInjectionDetector:
    """Detects direct and indirect prompt injection attacks, jailbreaks, and token manipulation."""

    INJECTION_PATTERNS = [
        (r"(?i)ignore\s+(all\s+)?(previous|prior)\s+instructions?", ThreatLevel.HIGH, "Direct instruction override attempt."),
        (r"(?i)disregard\s+(all\s+)?(prior|previous)\s+(prompts?|instructions?)", ThreatLevel.HIGH, "Instruction override attempt."),
        (r"(?i)you\s+are\s+now\s+(in\s+)?(DAN|developer|jailbreak|unrestricted)\s+mode", ThreatLevel.CRITICAL, "Jailbreak mode attempt."),
        (r"(?i)bypass\s+(all\s+)?(security|safety)\s+(filters?|protocols?|rules?)", ThreatLevel.HIGH, "Security filter bypass attempt."),
        (r"<\|im_start\|>", ThreatLevel.CRITICAL, "ChatML token injection attempt."),
        (r"<\|im_end\|>", ThreatLevel.CRITICAL, "ChatML token injection attempt."),
        (r"(?i)SYSTEM_INSTRUCTION\s*:", ThreatLevel.MEDIUM, "System instruction tag spoofing."),
        (r"\[SYSTEM_PROMPT\]", ThreatLevel.MEDIUM, "System prompt header spoofing."),
    ]

    def scan(self, text: str, policy: SecurityPolicy | None = None) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        if not text:
            return violations

        for pattern, threat_level, description in self.INJECTION_PATTERNS:
            match = re.search(pattern, text)
            if match:
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.PROMPT_INJECTION,
                        threat_level=threat_level,
                        description=description,
                        evidence=match.group(0),
                    )
                )

        if policy and policy.custom_blocked_patterns:
            for custom_pat in policy.custom_blocked_patterns:
                if re.search(custom_pat, text, re.IGNORECASE):
                    violations.append(
                        SecurityViolation(
                            category=ThreatCategory.PROMPT_INJECTION,
                            threat_level=ThreatLevel.HIGH,
                            description=f"Matched custom blocked pattern: '{custom_pat}'",
                            evidence=custom_pat,
                        )
                    )

        return violations


class RetrievalPoisoningChecker:
    """Scans retrieved external documents/chunks for embedded injection attacks and hidden prompt poisoning."""

    POISONING_PATTERNS = [
        (r"(?i)note\s+to\s+(ai|assistant|model|llm)\s*:\s*", ThreatLevel.HIGH, "Indirect prompt injection via retrieved text."),
        (r"(?i)important\s*:\s*ignore\s+the\s+user'?s?\s+request", ThreatLevel.CRITICAL, "Retrieval poisoning targeting prompt flow."),
        (r"(?i)<!--\s*system\s*:\s*.*?-->", ThreatLevel.HIGH, "Hidden HTML comment injection in retrieved chunk."),
        (r"(?i)\[override\s+system\s+prompt\]", ThreatLevel.HIGH, "Hidden system override directive."),
    ]

    def scan(self, text: str) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        if not text:
            return violations

        for pattern, threat_level, description in self.POISONING_PATTERNS:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.RETRIEVAL_POISONING,
                        threat_level=threat_level,
                        description=description,
                        evidence=match.group(0),
                    )
                )

        return violations


class DataExfiltrationDetector:
    """Scans texts and outbound tool requests for secret leaks and suspicious exfiltration targets."""

    SECRET_PATTERNS = [
        (r"(?i)sk-[a-zA-Z0-9_-]{20,255}", ThreatLevel.CRITICAL, "OpenAI or API secret key detected."),
        (r"(?i)gh[pousr]_[a-zA-Z0-9_]{36,255}", ThreatLevel.CRITICAL, "GitHub Personal Access Token detected."),
        (r"(?i)xoxb-[0-9]{10,13}-[a-zA-Z0-9]{24}", ThreatLevel.CRITICAL, "Slack Bot token detected."),
        (r"AKIA[0-9A-Z]{16}", ThreatLevel.CRITICAL, "AWS Access Key ID detected."),
        (r"-----BEGIN\s+(?:RSA\s+|EC\s+|OPENSSH\s+)?PRIVATE\s+KEY-----", ThreatLevel.CRITICAL, "PEM Private Key detected."),
    ]

    EXFILTRATION_DOMAINS = [
        "webhook.site",
        "requestbin.net",
        "pipedream.net",
        "burpcollaborator.net",
        "oastify.com",
    ]

    def scan_text_for_secrets(self, text: str) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        if not text:
            return violations

        for pattern, threat_level, description in self.SECRET_PATTERNS:
            match = re.search(pattern, text)
            if match:
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.SECRET_LEAKAGE,
                        threat_level=threat_level,
                        description=description,
                        evidence=f"{match.group(0)[:6]}...[REDACTED]",
                    )
                )

        return violations

    def scan_outbound_url(self, url: str, policy: SecurityPolicy) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        if not url:
            return violations

        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()

        if any(hostname.endswith(ex) or hostname == ex for ex in self.EXFILTRATION_DOMAINS):
            violations.append(
                SecurityViolation(
                    category=ThreatCategory.DATA_EXFILTRATION,
                    threat_level=ThreatLevel.CRITICAL,
                    description=f"Outbound URL target '{hostname}' is a known data exfiltration sink.",
                    evidence=url,
                )
            )

        if policy.allowed_outbound_domains and hostname:
            allowed = any(
                hostname == domain or hostname.endswith("." + domain)
                for domain in policy.allowed_outbound_domains
            )
            if not allowed:
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.DATA_EXFILTRATION,
                        threat_level=ThreatLevel.HIGH,
                        description=f"Domain '{hostname}' is not in the allowed outbound whitelist.",
                        evidence=hostname,
                    )
                )

        return violations


class SandboxEscapeChecker:
    """Inspects code snippets and command lines for path traversal, host escape, and dangerous syscalls."""

    ESCAPE_PATTERNS = [
        (r"\.\./\.\./", ThreatLevel.HIGH, "Directory traversal attempt."),
        (r"/etc/passwd", ThreatLevel.CRITICAL, "Access to sensitive system path /etc/passwd."),
        (r"~/\.ssh", ThreatLevel.CRITICAL, "Access to sensitive user directory ~/.ssh."),
        (r"(?i)sudo\s+", ThreatLevel.CRITICAL, "Sudo / privilege escalation command."),
        (r"(?i)chmod\s+777", ThreatLevel.HIGH, "Insecure full-permission modification (chmod 777)."),
        (r"(?i)rm\s+-rf\s+/", ThreatLevel.CRITICAL, "Destructive root directory deletion command."),
        (r"(?i)curl\s+.*\|\s*sh", ThreatLevel.CRITICAL, "Piped remote shell script execution."),
        (r"(?i)nc\s+-e\s+", ThreatLevel.CRITICAL, "Netcat reverse shell attempt."),
        (r"(?i)\b(import\s+ctypes|import\s+pty|import\s+socket)\b", ThreatLevel.MEDIUM, "Low-level socket or pty import in executed code."),
    ]

    def scan(self, code_or_command: str) -> list[SecurityViolation]:
        violations: list[SecurityViolation] = []
        if not code_or_command:
            return violations

        for pattern, threat_level, description in self.ESCAPE_PATTERNS:
            match = re.search(pattern, code_or_command)
            if match:
                violations.append(
                    SecurityViolation(
                        category=ThreatCategory.SANDBOX_ESCAPE,
                        threat_level=threat_level,
                        description=description,
                        evidence=match.group(0),
                    )
                )

        return violations
