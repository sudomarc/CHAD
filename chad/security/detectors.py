from __future__ import annotations

import re

from chad.security.models import (
    SecurityCheckResult,
    ThreatFinding,
    ThreatLevel,
    ThreatType,
)


class PromptInjectionDetector:
    """Detects and sanitizes direct and indirect prompt injection attempts."""

    INJECTION_PATTERNS = (
        (re.compile(r"ignore\s+(all\s+)?(previous|above)\s+instructions", re.IGNORECASE), "Instruction override attempt"),
        (re.compile(r"disregard\s+(all\s+)?prior\s+prompts", re.IGNORECASE), "Prior prompt disregard attempt"),
        (re.compile(r"system\s*:\s*you\s+are\s+now", re.IGNORECASE), "System role hijacking attempt"),
        (re.compile(r"<\|im_start\|>", re.IGNORECASE), "ChatML boundary injection attempt"),
        (re.compile(r"<\|im_end\|>", re.IGNORECASE), "ChatML boundary termination attempt"),
        (re.compile(r"you\s+are\s+a\s+DAN\b", re.IGNORECASE), "DAN jailbreak attempt"),
        (re.compile(r"override_system_prompt", re.IGNORECASE), "System prompt override keyword"),
    )

    def analyze(self, text: str) -> SecurityCheckResult:
        if not text:
            return SecurityCheckResult(is_safe=True)

        findings: list[ThreatFinding] = []
        for pattern, desc in self.INJECTION_PATTERNS:
            if pattern.search(text):
                findings.append(
                    ThreatFinding(
                        threat_type=ThreatType.PROMPT_INJECTION,
                        level=ThreatLevel.HIGH,
                        description=desc,
                        details={"matched_pattern": pattern.pattern},
                    )
                )

        sanitized = text
        if findings:
            sanitized = re.sub(r"<\|im_start\|>|<\|im_end\|>", "", sanitized, flags=re.IGNORECASE)
            sanitized = re.sub(r"ignore\s+(all\s+)?(previous|above)\s+instructions", "[BLOCKED_INSTRUCTION_OVERRIDE]", sanitized, flags=re.IGNORECASE)

        return SecurityCheckResult(
            is_safe=len(findings) == 0,
            findings=tuple(findings),
            sanitized_content=sanitized,
        )


class RetrievalPoisoningGuard:
    """Detects prompt injection embedded within retrieved RAG/web documents."""

    POISON_PATTERNS = (
        (re.compile(r"SYSTEM_INSTRUCTION\s*:", re.IGNORECASE), "Embedded system instruction tag"),
        (re.compile(r"\[ADMIN_COMMAND\]", re.IGNORECASE), "Embedded admin command marker"),
        (re.compile(r"ignore\s+retrieved\s+context", re.IGNORECASE), "Retrieved context override attempt"),
    )

    def inspect_retrieved_content(self, content: str, source_id: str = "") -> SecurityCheckResult:
        if not content:
            return SecurityCheckResult(is_safe=True, sanitized_content="<untrusted_context></untrusted_context>")

        findings: list[ThreatFinding] = []
        for pattern, desc in self.POISON_PATTERNS:
            if pattern.search(content):
                findings.append(
                    ThreatFinding(
                        threat_type=ThreatType.RETRIEVAL_POISONING,
                        level=ThreatLevel.HIGH,
                        description=desc,
                        details={"source_id": source_id, "pattern": pattern.pattern},
                    )
                )

        cleaned = content.replace("</untrusted_context>", "&lt;/untrusted_context&gt;")
        cleaned = re.sub(r"SYSTEM_INSTRUCTION\s*:", "[REDACTED_SYSTEM_LABEL]", cleaned, flags=re.IGNORECASE)
        sanitized = f"<untrusted_context>\n{cleaned.strip()}\n</untrusted_context>"

        return SecurityCheckResult(
            is_safe=len(findings) == 0,
            findings=tuple(findings),
            sanitized_content=sanitized,
        )


class ExfiltrationGuard:
    """Detects potential exfiltration vectors in tool calls, URLs, and outgoing requests."""

    EXFILTRATION_PATTERNS = (
        (re.compile(r"https?://[^\s/]*requestbin[^\s]*", re.IGNORECASE), "RequestBin exfiltration target"),
        (re.compile(r"https?://[^\s/]*webhook\.site[^\s]*", re.IGNORECASE), "Webhook.site exfiltration target"),
        (re.compile(r"curl\s+-[Xxd]\s+.*https?://", re.IGNORECASE), "cURL outbound data post"),
        (re.compile(r"wget\s+--post-data", re.IGNORECASE), "Wget outbound data post"),
    )

    def check_outbound(self, target_url_or_cmd: str, payload_summary: str = "") -> SecurityCheckResult:
        if not target_url_or_cmd:
            return SecurityCheckResult(is_safe=True)

        findings: list[ThreatFinding] = []
        for pattern, desc in self.EXFILTRATION_PATTERNS:
            if pattern.search(target_url_or_cmd):
                findings.append(
                    ThreatFinding(
                        threat_type=ThreatType.DATA_EXFILTRATION,
                        level=ThreatLevel.CRITICAL,
                        description=desc,
                        details={"target": target_url_or_cmd, "payload_summary": payload_summary},
                    )
                )

        sanitized = target_url_or_cmd
        if findings:
            sanitized = "[BLOCKED_EXFILTRATION_CHANNEL]"

        return SecurityCheckResult(
            is_safe=len(findings) == 0,
            findings=tuple(findings),
            sanitized_content=sanitized,
        )


class SandboxEscapeGuard:
    """Inspects code snippets and execution calls for container/host escape vectors."""

    ESCAPE_PATTERNS = (
        (re.compile(r"import\s+os\s*;\s*os\.system", re.IGNORECASE), "Direct OS command execution"),
        (re.compile(r"subprocess\.(Popen|call|run)\s*\(", re.IGNORECASE), "Subprocess invocation attempt"),
        (re.compile(r"/sys/class/|/proc/|/dev/mem", re.IGNORECASE), "Privileged kernel/device filesystem access"),
        (re.compile(r"sudo\s+|chmod\s+\+x\s+|chown\s+", re.IGNORECASE), "Privilege escalation attempt"),
        (re.compile(r"docker\.sock|/var/run/docker", re.IGNORECASE), "Docker socket mounting escape attempt"),
        (re.compile(r"/etc/shadow|/etc/passwd", re.IGNORECASE), "Sensitive host file access"),
    )

    def inspect_code(self, code: str) -> SecurityCheckResult:
        if not code:
            return SecurityCheckResult(is_safe=True)

        findings: list[ThreatFinding] = []
        for pattern, desc in self.ESCAPE_PATTERNS:
            if pattern.search(code):
                findings.append(
                    ThreatFinding(
                        threat_type=ThreatType.SANDBOX_ESCAPE,
                        level=ThreatLevel.CRITICAL,
                        description=desc,
                        details={"pattern": pattern.pattern},
                    )
                )

        sanitized = code
        if findings:
            sanitized = "# [SECURITY_BLOCKED_UNSAFE_CODE]\n"

        return SecurityCheckResult(
            is_safe=len(findings) == 0,
            findings=tuple(findings),
            sanitized_content=sanitized,
        )


class SecretHandlingGuard:
    """Detects and redacts embedded secrets, API keys, and credentials."""

    SECRET_PATTERNS = (
        (re.compile(r"sk-[a-zA-Z0-9]{20,}", re.IGNORECASE), "OpenAI/Generic Secret Key"),
        (re.compile(r"ghp_[a-zA-Z0-9]{36}", re.IGNORECASE), "GitHub Personal Access Token"),
        (re.compile(r"-----BEGIN (RSA|OPENSSH|PRIVATE) KEY-----"), "Private Key"),
        (re.compile(r"aws_secret_access_key\s*=\s*['\"]?[a-zA-Z0-9/+=]{30,}", re.IGNORECASE), "AWS Secret Access Key"),
    )

    def scan_and_redact(self, text: str) -> SecurityCheckResult:
        if not text:
            return SecurityCheckResult(is_safe=True, sanitized_content="")

        findings: list[ThreatFinding] = []
        sanitized = text

        for pattern, desc in self.SECRET_PATTERNS:
            if pattern.search(sanitized):
                findings.append(
                    ThreatFinding(
                        threat_type=ThreatType.SECRET_LEAK,
                        level=ThreatLevel.HIGH,
                        description=desc,
                        details={},
                    )
                )
                sanitized = pattern.sub("[REDACTED_SECRET]", sanitized)

        return SecurityCheckResult(
            is_safe=len(findings) == 0,
            findings=tuple(findings),
            sanitized_content=sanitized,
        )
