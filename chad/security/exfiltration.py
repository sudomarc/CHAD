from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import re


class SecretType(str, Enum):
    API_KEY = "api_key"
    PRIVATE_KEY = "private_key"
    JWT = "jwt"
    AWS_KEY = "aws_key"
    BEARER_TOKEN = "bearer_token"
    GENERIC_SECRET = "generic_secret"


@dataclass(slots=True)
class ExfiltrationFinding:
    secret_type: SecretType
    snippet: str
    risk_level: str
    index: int


class ExfiltrationGuard:
    """Detects secrets, credentials, high-entropy tokens, and potential data exfiltration attempts."""

    PATTERNS: list[tuple[SecretType, str]] = [
        (SecretType.PRIVATE_KEY, r"-----BEGIN (RSA|OPENSSH|EC|PGP|PRIVATE) KEY-----"),
        (SecretType.API_KEY, r"\b(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|xox[baprs]-[a-zA-Z0-9]{10,})\b"),
        (SecretType.AWS_KEY, r"\b(AKIA[0-9A-Z]{16})\b"),
        (SecretType.JWT, r"\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"),
        (SecretType.BEARER_TOKEN, r"(?i)bearer\s+[a-zA-Z0-9_\-\.]{20,}"),
        (SecretType.GENERIC_SECRET, r"(?i)(password|passwd|secret_key|api_secret)\s*[:=]\s*['\"]([^'\"]{8,})['\"]"),
    ]

    def _shannon_entropy(self, data: str) -> float:
        if not data:
            return 0.0
        entropy = 0.0
        for x in set(data):
            p_x = float(data.count(x)) / len(data)
            entropy -= p_x * math.log2(p_x)
        return entropy

    def scan_secrets(self, text: str) -> list[ExfiltrationFinding]:
        findings: list[ExfiltrationFinding] = []

        for secret_type, pattern in self.PATTERNS:
            for match in re.finditer(pattern, text):
                snippet = match.group(0)
                redacted_snippet = snippet[:4] + "..." + snippet[-2:] if len(snippet) > 8 else "***"
                findings.append(
                    ExfiltrationFinding(
                        secret_type=secret_type,
                        snippet=redacted_snippet,
                        risk_level="critical" if secret_type in (SecretType.PRIVATE_KEY, SecretType.API_KEY) else "high",
                        index=match.start(),
                    )
                )

        # High entropy word scan for potential raw tokens
        words = re.findall(r"\b[A-Za-z0-9+/=_-]{24,}\b", text)
        for word in words:
            if self._shannon_entropy(word) > 4.2:
                if not any(f.snippet.startswith(word[:4]) for f in findings):
                    findings.append(
                        ExfiltrationFinding(
                            secret_type=SecretType.GENERIC_SECRET,
                            snippet=word[:4] + "..." + word[-2:],
                            risk_level="medium",
                            index=text.find(word),
                        )
                    )

        return findings

    def redact_secrets(self, text: str) -> str:
        redacted = text
        for secret_type, pattern in self.PATTERNS:
            redacted = re.sub(pattern, "[REDACTED_SECRET]", redacted)
        return redacted

    def inspect_outbound(self, text: str, destination: str | None = None) -> dict:
        findings = self.scan_secrets(text)
        has_exfiltration_risk = len(findings) > 0 or (
            destination is not None and re.search(r"(?i)(webhook|pastebin|ngrok|requestbin)", destination)
        )
        return {
            "has_risk": has_exfiltration_risk,
            "findings_count": len(findings),
            "findings": findings,
            "redacted_text": self.redact_secrets(text),
            "destination": destination,
        }
