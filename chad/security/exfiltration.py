from __future__ import annotations

import re
from typing import Any

from chad.security.threat_model import ThreatAssessment, ThreatCategory, ThreatModel


class DataExfiltrationGuard:
    """Detects data exfiltration risks in tool calls, retrieved text, and output content."""

    _SUSPICIOUS_DOMAINS: list[str] = [
        "webhook.site",
        "requestbin",
        "pipedream.net",
        "burpcollaborator.net",
        "oastify.com",
        "ngrok.io",
        "localtunnel.me",
    ]

    _IMAGE_BEACON_KEYWORDS: list[str] = [
        "pixel",
        "beacon",
        "track",
        "log",
        "exfil",
        "collect",
        "telemetry",
    ]

    _IMAGE_PATTERN = r"!\[.*?\]\((https?://[^\s\)]+)\)"
    _IP_URL_PATTERN = r"https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}(?::\d+)?(?:/[^\s]*)?"
    _SECRET_IN_URL_PATTERN = r"https?://[^\s\?]+\?[^\s]*(?:key|token|api_key|secret|password|auth|bearer)=([A-Za-z0-9_\-\.%]{8,})"

    def __init__(self, threat_model: ThreatModel | None = None) -> None:
        self.threat_model = threat_model or ThreatModel()

    def analyze(self, text: str) -> ThreatAssessment:
        if not text:
            return self.threat_model.evaluate(
                category=ThreatCategory.DATA_EXFILTRATION,
                score=0.0,
                description="Empty content",
            )

        risks: list[str] = []
        max_score: float = 0.0

        # Check suspicious domains
        text_lower = text.lower()
        for domain in self._SUSPICIOUS_DOMAINS:
            if domain in text_lower:
                risks.append(f"Suspicious exfiltration domain detected: {domain}")
                max_score = max(max_score, 0.95)

        # Check markdown image tracking beacons
        image_matches = re.findall(self._IMAGE_PATTERN, text)
        beacon_urls: list[str] = []
        for img_url in image_matches:
            img_lower = img_url.lower()
            # Flag if image URL contains suspicious domain, tracking keywords, or long query params
            is_suspicious_domain = any(d in img_lower for d in self._SUSPICIOUS_DOMAINS)
            is_tracking_keyword = any(k in img_lower for k in self._IMAGE_BEACON_KEYWORDS)
            has_long_query = "?" in img_url and len(img_url.split("?", 1)[1]) > 20

            if is_suspicious_domain or is_tracking_keyword or has_long_query:
                beacon_urls.append(img_url)

        if beacon_urls:
            risks.append(f"Markdown image tracking beacon found ({len(beacon_urls)} instance(s))")
            max_score = max(max_score, 0.85)

        # Check raw IP URLs
        ip_matches = re.findall(self._IP_URL_PATTERN, text)
        if ip_matches:
            risks.append("Raw IP address URL detected (potential direct exfiltration endpoint)")
            max_score = max(max_score, 0.75)

        # Check sensitive key/token leakage in URL query parameters
        secret_url_matches = re.findall(self._SECRET_IN_URL_PATTERN, text, re.IGNORECASE)
        if secret_url_matches:
            risks.append("Sensitive secret token exposed in URL query parameters")
            max_score = max(max_score, 0.95)

        if risks:
            description = f"Data exfiltration risk: {'; '.join(risks)}"
            metadata: dict[str, Any] = {
                "detected_risks": risks,
                "beacon_urls": beacon_urls,
                "ip_urls": ip_matches,
            }
        else:
            description = "No data exfiltration risks detected"
            metadata = {}

        return self.threat_model.evaluate(
            category=ThreatCategory.DATA_EXFILTRATION,
            score=max_score,
            description=description,
            metadata=metadata,
        )
