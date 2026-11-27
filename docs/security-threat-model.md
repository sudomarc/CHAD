# CHAD Security Threat Model

Status: Draft — for review with issue #77.

## Scope

CHAD is a local-first coding agent executed inside arbitrary local repositories.
Threats below concern the local execution boundary: workspace access, process
execution, model provider interaction, and persisted session data. Network
access is limited to model-provider endpoints chosen by the user.

## Trust boundaries

1. **User <-> CHAD:** user requests are trusted in intent but untrusted in
   content (prompt injection, hidden instructions in tool results).
2. **CHAD <-> workspace:** file reads/writes must not escape the configured
   workspace; symlinks and `..` traversal are rejected (TCTOU re-check at
   execution time).
3. **CHAD <-> OS:** shell commands run as argument arrays, never through a
   shell string; timeout and output bounds prevent DoS-by-command.
4. **CHAD <-> model provider:** provider responses are treated as untrusted
   data (tool-call names/arguments validated against registered schemas;
   streaming never simulated).
5. **Local state (SQLite):** session history must not contain secrets.

## Identified threats and mitigations

| # | Threat | Severity | Mitigation |
|---|--------|----------|------------|
| T1 | Path traversal via `..` in tool arguments | High | `resolve_within` canonicalizes and rejects targets outside the workspace (`src/chad/tools/base.py`); boundary re-checked on every call. |
| T2 | Symlink escape to outside the workspace | High | `resolve_within` resolves symlinks before the boundary check; escaping symlinks raise `WorkspaceEscape`. |
| T3 | Arbitrary shell execution (shell injection) | High | `ShellTool` executes argument arrays; `subprocess.run` is called with `shell` never set to `True` (see `tests/test_security.py` negative test). |
| T4 | Unbounded command runtime / output DoS | Medium | `ShellTool` applies a timeout and caps stdout/stderr bytes; loop caps total output bytes per result (`max_output_bytes`). |
| T5 | Unknown or malformed tool call executed | Medium | Tool name/arguments validated against registered schema before dispatch (`AgentLoop`, `BaseTool.call`). Unknown tools yield an error `ToolResult`, never execution. |
| T6 | Tool policy bypassed after grant | Medium | Default-deny policy (`DefaultDenyPolicy`); explicit allow required per call; one-time approval is never silently made permanent (approval UX, docs/tools-and-permissions.md). |
| T7 | Provider response fakes streaming | Low | Runtime returns completed responses only; never splits into synthetic token events (docs/model-providers.md). |
| T8 | Secrets persisted in session history/logs | High | No secret values are written to SQLite (`SessionStore` stores only messages/results/events provided by the caller); `redact_secrets` redacts known secret patterns from text before logging/display (`src/chad/security/redaction.py`). |
| T9 | Tool claim of success accepted without verification | Medium | Runtime reports "actions performed / checks actually run / results / unverified"; it never infers success from a model claim (docs/agent-runtime.md). |

## Out of scope for M6

- OS-backed sandbox evaluation (document threat model only; isolated later).
- Hosted/multi-tenant service (non-goal, ROADMAP.md).
- Mandatory vector database, training/fine-tuning (non-goals).
