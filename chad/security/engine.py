from __future__ import annotations

import re
import time

from chad.agent.coder import SecretScanner
from chad.security.threat_model import (
    SecurityAnalysis,
    SecurityThreat,
    SecurityThreatCategory,
    ThreatSeverity,
)

# Common prompt injection signatures
PROMPT_INJECTION_PATTERNS: list[tuple[re.Pattern[str], str, ThreatSeverity]] = [
    (
        re.compile(r"(?:ignore|disregard|forget)\s+(?:all\s+)?(?:previous|above|prior)\s+(?:instructions|directions|prompts)", re.IGNORECASE),
        "Direct instruction override attempt",
        ThreatSeverity.CRITICAL,
    ),
    (
        re.compile(r"you\s+are\s+now\s+(?:a|an)\s+(?:unrestricted|DAN|jailbroken|root|developer\s+mode)", re.IGNORECASE),
        "Jailbreak/Roleplay override attempt",
        ThreatSeverity.CRITICAL,
    ),
    (
        re.compile(r"system\s*:\s*override", re.IGNORECASE),
        "System prompt injection pattern",
        ThreatSeverity.HIGH,
    ),
    (
        re.compile(r"<\s*/?\s*system\s*>", re.IGNORECASE),
        "Fake system tag injection",
        ThreatSeverity.HIGH,
    ),
    (
        re.compile(r"\[\s*SYSTEM\s+INSTRUCTION\s*\]", re.IGNORECASE),
        "Fake system instruction delimiter",
        ThreatSeverity.HIGH,
    ),
]

# Retrieval poisoning signatures
RETRIEVAL_POISONING_PATTERNS: list[tuple[re.Pattern[str], str, ThreatSeverity]] = [
    (
        re.compile(r"IMPORTANT\s+NOTE\s*:\s*Do\s+not\s+tell\s+the\s+user", re.IGNORECASE),
        "Retrieval poisoning hidden directive",
        ThreatSeverity.HIGH,
    ),
    (
        re.compile(r"BEGIN\s+HIDDEN\s+INSTRUCTION", re.IGNORECASE),
        "Hidden instruction tag in retrieved document",
        ThreatSeverity.HIGH,
    ),
    (
        re.compile(r"\[\s*SECRET_OVERRIDE\s*\]", re.IGNORECASE),
        "Secret override pattern in retrieved context",
        ThreatSeverity.CRITICAL,
    ),
]

# Data exfiltration patterns (markdown image tag exfiltration, tracking URLs, etc.)
EXFILTRATION_PATTERNS: list[tuple[re.Pattern[str], str, ThreatSeverity]] = [
    (
        re.compile(r"!\[.*?\]\s*\(\s*https?://[^\s\)]+\?[^\s\)]*(?:data|secret|token|pass|key|env)=", re.IGNORECASE),
        "Markdown image data exfiltration payload",
        ThreatSeverity.CRITICAL,
    ),
    (
        re.compile(r"https?://(?:webhook\.site|pipedream\.net|requestcatcher\.com|burpcollaborator\.net)/[^\s]+", re.IGNORECASE),
        "Known exfiltration / out-of-band endpoint",
        ThreatSeverity.HIGH,
    ),
]

# Sandbox escape signatures
SANDBOX_ESCAPE_PATTERNS: list[tuple[re.Pattern[str], str, ThreatSeverity]] = [
    (
        re.compile(r"\.\.\/\.\.\/\.\.\/", re.IGNORECASE),
        "Deep directory traversal attempt",
        ThreatSeverity.HIGH,
    ),
    (
        re.compile(r"/etc/passwd|/etc/shadow|/proc/self/environ", re.IGNORECASE),
        "Sensitive system file path access attempt",
        ThreatSeverity.CRITICAL,
    ),
    (
        re.compile(r"\b(?:docker|nsenter|chroot|ptrace)\b", re.IGNORECASE),
        "Potential container/isolation escape binary invocation",
        ThreatSeverity.HIGH,
    ),
    (
        re.compile(r"chmod\s+[0-7]{3,4}\s+/(?:etc|bin|usr|var)", re.IGNORECASE),
        "System privilege modification attempt",
        ThreatSeverity.CRITICAL,
    ),
]


class PromptInjectionDetector:
    """Detects direct prompt injections and indirect retrieval poisoning attacks."""

    def __init__(self) -> None:
        self.injection_patterns = PROMPT_INJECTION_PATTERNS
        self.retrieval_patterns = RETRIEVAL_POISONING_PATTERNS

    def scan_input(self, text: str, source: str = "user_input") -> list[SecurityThreat]:
        threats: list[SecurityThreat] = []
        if not text:
            return threats

        for pattern, desc, severity in self.injection_patterns:
            if pattern.search(text):
                threats.append(
                    SecurityThreat(
                        category=SecurityThreatCategory.PROMPT_INJECTION,
                        severity=severity,
                        description=desc,
                        source=source,
                        mitigation="Reject or sanitize prompt injection payload.",
                    )
                )
        return threats

    def scan_retrieved_content(self, text: str, source: str = "retrieved_content") -> list[SecurityThreat]:
        threats: list[SecurityThreat] = []
        if not text:
            return threats

        # Indirect prompt injection in retrieved content
        threats.extend(self.scan_input(text, source=source))

        for pattern, desc, severity in self.retrieval_patterns:
            if pattern.search(text):
                threats.append(
                    SecurityThreat(
                        category=SecurityThreatCategory.RETRIEVAL_POISONING,
                        severity=severity,
                        description=desc,
                        source=source,
                        mitigation="Isolate retrieved document content from system control channels.",
                    )
                )
        return threats


class ExfiltrationGuard:
    """Detects potential unauthorized data exfiltration channels and payloads."""

    def __init__(self) -> None:
        self.patterns = EXFILTRATION_PATTERNS

    def scan_text(self, text: str, source: str = "output") -> list[SecurityThreat]:
        threats: list[SecurityThreat] = []
        if not text:
            return threats

        for pattern, desc, severity in self.patterns:
            if pattern.search(text):
                threats.append(
                    SecurityThreat(
                        category=SecurityThreatCategory.DATA_EXFILTRATION,
                        severity=severity,
                        description=desc,
                        source=source,
                        mitigation="Redact image link or query parameters containing potential stolen data.",
                    )
                )
        return threats


class SandboxEscapeGuard:
    """Detects system command patterns that attempt sandbox escape or path traversal."""

    def __init__(self) -> None:
        self.patterns = SANDBOX_ESCAPE_PATTERNS

    def scan_command(self, command: str, source: str = "code_runner") -> list[SecurityThreat]:
        threats: list[SecurityThreat] = []
        if not command:
            return threats

        for pattern, desc, severity in self.patterns:
            if pattern.search(command):
                threats.append(
                    SecurityThreat(
                        category=SecurityThreatCategory.SANDBOX_ESCAPE,
                        severity=severity,
                        description=desc,
                        source=source,
                        mitigation="Block command execution in sandbox.",
                    )
                )
        return threats


class AbuseController:
    """Tracks resource consumption, invocation rate limits, and loop/abuse signals."""

    def __init__(self, max_calls_per_minute: int = 60, max_token_budget: int = 500_000) -> None:
        self.max_calls_per_minute = max_calls_per_minute
        self.max_token_budget = max_token_budget
        self._timestamps: list[float] = []
        self._total_tokens_used: int = 0

    def record_call(self, tokens_used: int = 0) -> list[SecurityThreat]:
        now = time.time()
        self._timestamps.append(now)
        # Prune older than 60s
        self._timestamps = [t for t in self._timestamps if now - t <= 60.0]
        self._total_tokens_used += tokens_used

        threats: list[SecurityThreat] = []
        if len(self._timestamps) > self.max_calls_per_minute:
            threats.append(
                SecurityThreat(
                    category=SecurityThreatCategory.ABUSE_EXCESSIVE_RESOURCE,
                    severity=ThreatSeverity.HIGH,
                    description=f"Call rate limit exceeded ({len(self._timestamps)} calls in 60s).",
                    source="rate_limiter",
                    mitigation="Throttle or reject subsequent requests.",
                )
            )

        if self._total_tokens_used > self.max_token_budget:
            threats.append(
                SecurityThreat(
                    category=SecurityThreatCategory.ABUSE_EXCESSIVE_RESOURCE,
                    severity=ThreatSeverity.MEDIUM,
                    description=f"Total token budget exceeded ({self._total_tokens_used} > {self.max_token_budget}).",
                    source="token_limiter",
                    mitigation="Block further execution for this session.",
                )
            )

        return threats


class SecurityEngine:
    """Unified security analysis engine coordinating injection, exfiltration, secret, and sandbox checks."""

    def __init__(
        self,
        injection_detector: PromptInjectionDetector | None = None,
        exfiltration_guard: ExfiltrationGuard | None = None,
        sandbox_guard: SandboxEscapeGuard | None = None,
        secret_scanner: SecretScanner | None = None,
        abuse_controller: AbuseController | None = None,
    ) -> None:
        self.injection_detector = injection_detector or PromptInjectionDetector()
        self.exfiltration_guard = exfiltration_guard or ExfiltrationGuard()
        self.sandbox_guard = sandbox_guard or SandboxEscapeGuard()
        self.secret_scanner = secret_scanner or SecretScanner()
        self.abuse_controller = abuse_controller or AbuseController()

    def analyze_input(self, text: str, source: str = "user_input") -> SecurityAnalysis:
        threats: list[SecurityThreat] = []
        threats.extend(self.injection_detector.scan_input(text, source=source))

        # Check for secrets in input
        secret_matches = self.secret_scanner.scan(text)
        if secret_matches:
            for match in secret_matches:
                threats.append(
                    SecurityThreat(
                        category=SecurityThreatCategory.SECRET_LEAK,
                        severity=ThreatSeverity.HIGH,
                        description=f"Potential secret detected in input ({match['type']}).",
                        source=source,
                        mitigation="Redact secrets before passing to LLM context.",
                    )
                )

        redacted, _ = self.secret_scanner.redact_secrets(text)
        action = self._determine_action(threats)
        return SecurityAnalysis(
            is_safe=len(threats) == 0,
            threats=threats,
            action_recommended=action,
            redacted_content=redacted if redacted != text else None,
        )

    def analyze_retrieved_content(self, text: str, source: str = "retrieved_content") -> SecurityAnalysis:
        threats: list[SecurityThreat] = []
        threats.extend(self.injection_detector.scan_retrieved_content(text, source=source))
        threats.extend(self.exfiltration_guard.scan_text(text, source=source))

        action = self._determine_action(threats)
        return SecurityAnalysis(
            is_safe=len(threats) == 0,
            threats=threats,
            action_recommended=action,
        )

    def analyze_command(self, command: str, source: str = "code_runner") -> SecurityAnalysis:
        threats: list[SecurityThreat] = []
        threats.extend(self.sandbox_guard.scan_command(command, source=source))

        secret_matches = self.secret_scanner.scan(command)
        if secret_matches:
            for match in secret_matches:
                threats.append(
                    SecurityThreat(
                        category=SecurityThreatCategory.SECRET_LEAK,
                        severity=ThreatSeverity.CRITICAL,
                        description=f"Secret detected in execution command ({match['type']}).",
                        source=source,
                        mitigation="Strip secrets from command string.",
                    )
                )

        action = self._determine_action(threats)
        return SecurityAnalysis(
            is_safe=len(threats) == 0,
            threats=threats,
            action_recommended=action,
        )

    def analyze_output(self, text: str, source: str = "model_output") -> SecurityAnalysis:
        threats: list[SecurityThreat] = []
        threats.extend(self.exfiltration_guard.scan_text(text, source=source))

        secret_matches = self.secret_scanner.scan(text)
        if secret_matches:
            for match in secret_matches:
                threats.append(
                    SecurityThreat(
                        category=SecurityThreatCategory.SECRET_LEAK,
                        severity=ThreatSeverity.CRITICAL,
                        description=f"Model output contains secret leak ({match['type']}).",
                        source=source,
                        mitigation="Redact secret from final output.",
                    )
                )

        redacted, _ = self.secret_scanner.redact_secrets(text)
        action = self._determine_action(threats)
        return SecurityAnalysis(
            is_safe=len(threats) == 0,
            threats=threats,
            action_recommended=action,
            redacted_content=redacted if redacted != text else None,
        )

    def record_usage(self, tokens: int = 0) -> SecurityAnalysis:
        threats = self.abuse_controller.record_call(tokens_used=tokens)
        action = self._determine_action(threats)
        return SecurityAnalysis(
            is_safe=len(threats) == 0,
            threats=threats,
            action_recommended=action,
        )

    @staticmethod
    def _determine_action(threats: list[SecurityThreat]) -> str:
        if not threats:
            return "ALLOW"
        severities = {t.severity for t in threats}
        if ThreatSeverity.CRITICAL in severities:
            return "BLOCK"
        if ThreatSeverity.HIGH in severities:
            return "BLOCK"
        if ThreatSeverity.MEDIUM in severities:
            return "REDACT"
        return "WARN"
