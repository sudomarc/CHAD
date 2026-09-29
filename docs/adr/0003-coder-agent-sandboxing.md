# ADR 0003: Coder Agent Workspace Sandboxing and Command Execution Policy

## Context

The Coder Agent in CHAD is tasked with inspecting repository code, modifying files, applying diffs, and executing test commands.
Allowing unrestricted file access or arbitrary shell execution presents significant security risks, including directory traversal, secret leakage, and command injection or destruction.

## Decision

We introduce a dedicated Coder Agent subsystem (`chad.agent.coder`) with five enforcing layers:

1. **RepositoryWorkspace**: All file operations (`read_file`, `write_file`, `list_files`, `apply_diff`) are strictly bounded to a root workspace directory using `Path.resolve()` and `Path.relative_to()`. Any attempted path traversal outside the workspace throws a `ValueError`.
2. **SecretScanner**: Text, file contents, diffs, and command outputs are scanned against regex patterns for sensitive tokens (AWS keys, GitHub tokens, API keys, Bearer tokens, private keys). Detected secrets are redacted automatically with `[REDACTED_SECRET:<type>]`.
3. **CommandPolicy**: Explicit allowlisting for safe commands (e.g. `pytest`, `python`, `git`, `ls`, `cat`, `grep`, `ruff`, `mypy`) and forbidden pattern matching (blocking `rm -rf`, `sudo`, piping to shell like `curl | sh`, `eval`/`exec`).
4. **SandboxedCodeRuntime**: Subprocess execution with strict wall-clock timeout enforcement, environment variable cleansing (removing API keys from environment variables passed to child processes), and automatic output secret redaction.
5. **CoderEngine**: High-level coordinator providing structured results (`CoderResult`) for agent step execution.

## Consequences

- Prevents directory traversal attacks and accidental host file modifications outside the workspace.
- Protects API credentials and secret tokens from leaking into logs or model context.
- Restricts command execution to safe developer tools.
- Provides predictable execution timeouts and error handling for automated coding loops.

## Verification

- Covered by unit and integration tests in `tests/test_coder_agent.py`.
- Regression testing integrated into `PYTHONPATH=. python3 -m pytest`.
