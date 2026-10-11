# CHAD Security Model & Architecture

## 1. Trust Boundaries & Hierarchy

CHAD operates with strict defense-in-depth ordering across data sources and context channels:

```text
SYSTEM POLICY (Trusted)
   >
APPLICATION STATE (Trusted)
   >
USER REQUEST (Untrusted)
   >
MODEL OUTPUT (Untrusted)
   >
RETRIEVED CONTENT / FILES / WEB / TOOL OUTPUT (Untrusted)
```

Lower trust data must never alter or overwrite higher-trust policies or instruction channels.

## 2. Security Threat Taxonomy

CHAD defines six major threat categories managed by the `SecurityEngine`:

1. **Prompt Injection (`PROMPT_INJECTION`)**: Direct user or external attempts to override system instructions or jailbreak model persona.
2. **Retrieval Poisoning (`RETRIEVAL_POISONING`)**: Indirect injection embedded inside retrieved files, web pages, or RAG search chunks trying to hijack execution flow.
3. **Data Exfiltration (`DATA_EXFILTRATION`)**: Payloads (e.g., hidden markdown image tracking URLs, out-of-band request endpoints) attempting to exfiltrate private conversation context or secrets.
4. **Sandbox Escape (`SANDBOX_ESCAPE`)**: Execution or tool parameters attempting path traversal (`../`), privilege escalation, or container/host environment escape.
5. **Secret Leak (`SECRET_LEAK`)**: Exposure of API keys, tokens, or credentials in prompt context, command strings, or model outputs.
6. **Abuse & Excessive Resource Consumption (`ABUSE_EXCESSIVE_RESOURCE`)**: Unbounded loop, denial of service, rate limit, or token quota exhaustion.

## 3. Defense Mechanisms

### Security Engine (`chad.security.SecurityEngine`)

Centralized coordination engine for real-time security inspection across inputs, retrieved contexts, tool execution commands, outputs, and rate limits.

- **`PromptInjectionDetector`**: Regex and semantic heuristics for direct and indirect instruction hijacking.
- **`ExfiltrationGuard`**: Inspects image tags and URLs for data leak vectors.
- **`SandboxEscapeGuard`**: Enforces strict path and syscall isolation for code execution.
- **`SecretScanner`**: Automatic pattern detection and `[REDACTED_SECRET]` scrubbing.
- **`AbuseController`**: Sliding-window rate limiting and session token budgets.

### Security Actions

- **`ALLOW`**: Input/output is clean and permitted.
- **`WARN`**: Minor anomaly detected, logged for audit.
- **`REDACT`**: Sensitive secrets or exfiltration parameters automatically scrubbed.
- **`BLOCK`**: High/Critical severity threat detected; execution halted.

## 4. Audit & Compliance

All security evaluations generate structured `SecurityAnalysis` reports containing:
- `is_safe`: Boolean indicator
- `threats`: Detailed list of `SecurityThreat` objects with category, severity, source, and mitigation advice
- `action_recommended`: Recommendation for downstream orchestrator enforcement
- `redacted_content`: Sanitized text string when applicable
