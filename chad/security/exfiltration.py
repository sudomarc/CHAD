from __future__ import annotations

import re
from dataclasses import dataclass
from typing import ClassVar

from chad.agent.coder import SecretScanner
from chad.security.threat_model import SecurityThreat, ThreatCategory, ThreatLevel


@dataclass(frozen=True, slots=True)
class ExfiltrationScanResult:
    is_risk_detected: bool
    risk_reasons: tuple[str, ...]
    sanitized_output: str
    secrets_count: int = 0
    threats: tuple[SecurityThreat, ...] = ()


class ExfiltrationGuard:
    """Guards against data exfiltration, secret leakage, and unauthorized egress points."""

    EGRESS_PATTERNS: ClassVar[list[tuple[re.Pattern[str], str]]] = [
        (
            re.compile(r"https?://[^\s<'\"]+", re.IGNORECASE),
            "URL detected in output",
        ),
        (
            re.compile(r"curl\s+-[XdD]\s+.*https?://", re.IGNORECASE),
            "Curl data posting payload detected",
        ),
        (
            re.compile(r"wget\s+--post-(data|file)", re.IGNORECASE),
            "Wget post request payload detected",
        ),
        (
            re.compile(r"b64decode|base64\s+-d", re.IGNORECASE),
            "Base64 encoded data extraction attempt",
        ),
    ]

    def __init__(self, secret_scanner: SecretScanner | None = None, allowed_domains: list[str] | None = None) -> None:
        self.secret_scanner = secret_scanner or SecretScanner()
        self.allowed_domains = allowed_domains or ["example.com", "github.com", "pypi.org"]

    def scan_output(self, output: str, source: str = "assistant_output") -> ExfiltrationScanResult:
        if not output:
            return ExfiltrationScanResult(
                is_risk_detected=False, risk_reasons=(), sanitized_output=""
            )

        found_secret_matches = self.secret_scanner.scan(output)
        sanitized_output, secrets_count = self.secret_scanner.redact_secrets(output)
        risk_reasons: list[str] = []
        threats: list[SecurityThreat] = []

        if secrets_count > 0:
            secret_types = list({s.get("type", "unknown") for s in found_secret_matches}) or ["detected_secret"]
            reason = f"Secret leakage detected: {', '.join(secret_types)}"
            risk_reasons.append(reason)
            threats.append(
                SecurityThreat(
                    id=f"exfil-sec-{abs(hash(output)) % 100000:05d}",
                    category=ThreatCategory.SECRET_LEAKAGE,
                    level=ThreatLevel.CRITICAL,
                    description=reason,
                    source=source,
                    details={"secrets_count": secrets_count, "types": secret_types},
                )
            )

        for pattern, desc in self.EGRESS_PATTERNS:
            matches = pattern.findall(output)
            if matches:
                # Check domain whitelist if URLs were found
                if "URL" in desc:
                    unauthorized_urls = []
                    for match in matches:
                        url_str = match if isinstance(match, str) else match[0]
                        domain_match = re.search(r"https?://([^/:\s]+)", url_str)
                        if domain_match:
                            domain = domain_match.group(1).lower()
                            if not any(domain == allowed or domain.endswith(f".{allowed}") for allowed in self.allowed_domains):
                                unauthorized_urls.append(url_str)
                    if unauthorized_urls:
                        reason = f"Potential unauthorized egress URL: {', '.join(unauthorized_urls[:3])}"
                        risk_reasons.append(reason)
                        threats.append(
                            SecurityThreat(
                                id=f"exfil-url-{abs(hash(output)) % 100000:05d}",
                                category=ThreatCategory.DATA_EXFILTRATION,
                                level=ThreatLevel.HIGH,
                                description=reason,
                                source=source,
                                details={"unauthorized_urls": unauthorized_urls},
                            )
                        )
                else:
                    risk_reasons.append(desc)
                    threats.append(
                        SecurityThreat(
                            id=f"exfil-cmd-{abs(hash(output)) % 100000:05d}",
                            category=ThreatCategory.DATA_EXFILTRATION,
                            level=ThreatLevel.HIGH,
                            description=desc,
                            source=source,
                            details={"pattern": desc},
                        )
                    )

        return ExfiltrationScanResult(
            is_risk_detected=len(risk_reasons) > 0,
            risk_reasons=tuple(risk_reasons),
            sanitized_output=sanitized_output,
            secrets_count=secrets_count,
            threats=tuple(threats),
        )
