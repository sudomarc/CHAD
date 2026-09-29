from __future__ import annotations

import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Common secret detection patterns
SECRET_PATTERNS: dict[str, re.Pattern[str]] = {
    "AWS Key": re.compile(r"(?:AKIA|ASIA)[0-9A-Z]{16}"),
    "GitHub Token": re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"),
    "OpenAI/Anthropic API Key": re.compile(r"sk-[a-zA-Z0-9_-]{20,255}"),
    "Bearer/JWT Token": re.compile(r"eyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+"),
    "Private Key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "Generic API Key / Token": re.compile(
        r"(?:api[_-]?key|secret|password|auth[_-]?token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{16,})['\"]?",
        re.IGNORECASE,
    ),
}

DEFAULT_ALLOWED_COMMANDS: set[str] = {
    "pytest",
    "python",
    "python3",
    "git",
    "ls",
    "cat",
    "grep",
    "find",
    "echo",
    "ruff",
    "mypy",
    "black",
}

FORBIDDEN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\brm\s+-rf\b"),
    re.compile(r"\bsudo\b"),
    re.compile(r"\|\s*sh\b"),
    re.compile(r"\|\s*bash\b"),
    re.compile(r"\bcurl\b.*\|\s*"),
    re.compile(r"\bwget\b.*\|\s*"),
    re.compile(r"\b(eval|exec)\b"),
]


class SecretScanner:
    """Scans text for sensitive patterns and provides secret redaction."""

    def __init__(self, custom_patterns: dict[str, re.Pattern[str]] | None = None) -> None:
        self.patterns = dict(SECRET_PATTERNS)
        if custom_patterns:
            self.patterns.update(custom_patterns)

    def scan(self, text: str) -> list[dict[str, str]]:
        """Scans text for secrets and returns details of found secrets."""
        if not text:
            return []
        matches: list[dict[str, str]] = []
        for name, pattern in self.patterns.items():
            for match in pattern.finditer(text):
                secret_str = match.group(0)
                masked = secret_str[:4] + "..." + secret_str[-4:] if len(secret_str) > 8 else "***"
                matches.append({"type": name, "match": masked})
        return matches

    def redact_secrets(self, text: str) -> tuple[str, int]:
        """Redacts all detected secrets in text with [REDACTED_SECRET].

        Returns tuple of (redacted_text, redacted_count).
        """
        if not text:
            return "", 0
        redacted_text = text
        count = 0
        for name, pattern in self.patterns.items():
            matches = list(pattern.finditer(redacted_text))
            if matches:
                count += len(matches)
                redacted_text = pattern.sub(f"[REDACTED_SECRET:{name}]", redacted_text)
        return redacted_text, count


class RepositoryWorkspace:
    """Provides sandboxed file operations over a root repository directory."""

    def __init__(self, root_path: str | Path) -> None:
        self.root_path = Path(root_path).resolve()
        if not self.root_path.exists():
            self.root_path.mkdir(parents=True, exist_ok=True)

    def resolve_path(self, relative_path: str | Path) -> Path:
        """Resolves relative path within workspace and prevents path traversal attacks."""
        resolved = (self.root_path / relative_path).resolve()
        try:
            resolved.relative_to(self.root_path)
        except ValueError as exc:
            raise ValueError(
                f"Path traversal detected: path '{relative_path}' is outside workspace root '{self.root_path}'."
            ) from exc
        return resolved

    def read_file(self, relative_path: str | Path, max_bytes: int = 100_000) -> str:
        """Reads text file inside workspace safely."""
        target = self.resolve_path(relative_path)
        if not target.is_file():
            raise FileNotFoundError(f"File '{relative_path}' does not exist in workspace.")
        content = target.read_text(encoding="utf-8")
        if len(content.encode("utf-8")) > max_bytes:
            return content[:max_bytes] + "\n...[truncated]"
        return content

    def write_file(self, relative_path: str | Path, content: str) -> None:
        """Writes text file inside workspace safely, creating parent directories if needed."""
        target = self.resolve_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def list_files(self, relative_path: str | Path = "") -> list[str]:
        """Lists relative file paths within workspace subfolder."""
        target_dir = self.resolve_path(relative_path)
        if not target_dir.is_dir():
            return []
        files: list[str] = []
        for path in target_dir.rglob("*"):
            if path.is_file():
                rel = path.relative_to(self.root_path)
                files.append(str(rel))
        return sorted(files)

    def apply_diff(self, relative_path: str | Path, diff_text: str) -> None:
        """Applies diff changes (Git merge diff format or replacement blocks) to a workspace file.

        Git merge diff format:
        <<<<<<< SEARCH
        original text
        =======
        replacement text
        >>>>>>> REPLACE
        """
        target = self.resolve_path(relative_path)
        current_content = target.read_text(encoding="utf-8") if target.exists() else ""

        # Parse Git merge diff blocks
        pattern = re.compile(
            r"<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE",
            re.DOTALL,
        )

        matches = list(pattern.finditer(diff_text))
        if not matches:
            raise ValueError("Invalid diff format: missing search/replace blocks.")

        updated_content = current_content
        for match in matches:
            search_block = match.group(1)
            replace_block = match.group(2)
            if search_block not in updated_content:
                raise ValueError(
                    f"Diff application failed: SEARCH block not found in file '{relative_path}'."
                )
            updated_content = updated_content.replace(search_block, replace_block, 1)

        self.write_file(relative_path, updated_content)


class CommandPolicy:
    """Policy engine enforcing allowed and forbidden execution commands."""

    def __init__(
        self,
        allowed_commands: set[str] | None = None,
        forbidden_patterns: list[re.Pattern[str]] | None = None,
    ) -> None:
        self.allowed_commands = allowed_commands or set(DEFAULT_ALLOWED_COMMANDS)
        self.forbidden_patterns = forbidden_patterns or list(FORBIDDEN_PATTERNS)

    def is_permitted(self, command: str) -> tuple[bool, str]:
        """Validates command against security policy."""
        cleaned = command.strip()
        if not cleaned:
            return False, "Empty command."

        for pattern in self.forbidden_patterns:
            if pattern.search(cleaned):
                return False, f"Command contains forbidden pattern matching '{pattern.pattern}'."

        base_cmd = cleaned.split()[0]
        # Remove path prefixes if given e.g. /usr/bin/pytest -> pytest
        base_name = Path(base_cmd).name
        if base_name not in self.allowed_commands:
            return False, f"Command '{base_name}' is not in allowed command list."

        return True, "Command permitted."


@dataclass(frozen=True, slots=True)
class CodeExecutionResult:
    exit_code: int
    stdout: str
    stderr: str
    execution_time_seconds: float
    timed_out: bool = False
    secrets_detected_count: int = 0


class SandboxedCodeRuntime:
    """Runs commands in an isolated subprocess environment with timeouts and output redaction."""

    def __init__(
        self,
        workspace: RepositoryWorkspace,
        policy: CommandPolicy | None = None,
        secret_scanner: SecretScanner | None = None,
        default_timeout: float = 30.0,
    ) -> None:
        self.workspace = workspace
        self.policy = policy or CommandPolicy()
        self.secret_scanner = secret_scanner or SecretScanner()
        self.default_timeout = default_timeout

    def run_command(
        self,
        command: str,
        timeout: float | None = None,
        env: dict[str, str] | None = None,
    ) -> CodeExecutionResult:
        """Executes a command within the workspace sandbox safely."""
        permitted, reason = self.policy.is_permitted(command)
        if not permitted:
            return CodeExecutionResult(
                exit_code=126,
                stdout="",
                stderr=f"Command execution denied by policy: {reason}",
                execution_time_seconds=0.0,
            )

        effective_timeout = timeout or self.default_timeout
        exec_env = dict(os.environ)
        # Strip sensitive credentials from subprocess environment
        for secret_var in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "AWS_SECRET_ACCESS_KEY", "GITHUB_TOKEN"):
            exec_env.pop(secret_var, None)
        if env:
            exec_env.update(env)

        start_time = time.time()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.workspace.root_path),
                capture_output=True,
                text=True,
                timeout=effective_timeout,
                env=exec_env,
                check=False,
            )
            elapsed = time.time() - start_time

            redacted_stdout, count_out = self.secret_scanner.redact_secrets(proc.stdout)
            redacted_stderr, count_err = self.secret_scanner.redact_secrets(proc.stderr)

            return CodeExecutionResult(
                exit_code=proc.returncode,
                stdout=redacted_stdout,
                stderr=redacted_stderr,
                execution_time_seconds=elapsed,
                timed_out=False,
                secrets_detected_count=count_out + count_err,
            )

        except subprocess.TimeoutExpired:
            elapsed = time.time() - start_time
            return CodeExecutionResult(
                exit_code=124,
                stdout="",
                stderr=f"Execution timed out after {effective_timeout} seconds.",
                execution_time_seconds=elapsed,
                timed_out=True,
                secrets_detected_count=0,
            )


@dataclass(frozen=True, slots=True)
class CoderResult:
    action: str
    success: bool
    details: str
    execution_result: CodeExecutionResult | None = None
    file_path: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "success": self.success,
            "details": self.details,
            "file_path": self.file_path,
            "execution_result": {
                "exit_code": self.execution_result.exit_code,
                "stdout": self.execution_result.stdout,
                "stderr": self.execution_result.stderr,
                "execution_time_seconds": self.execution_result.execution_time_seconds,
            }
            if self.execution_result
            else None,
        }


class CoderEngine:
    """High-level coordinator for Coder agent operations, repository edits, and test execution."""

    def __init__(
        self,
        workspace: RepositoryWorkspace,
        policy: CommandPolicy | None = None,
        secret_scanner: SecretScanner | None = None,
    ) -> None:
        self.workspace = workspace
        self.secret_scanner = secret_scanner or SecretScanner()
        self.policy = policy or CommandPolicy()
        self.runtime = SandboxedCodeRuntime(
            workspace=self.workspace,
            policy=self.policy,
            secret_scanner=self.secret_scanner,
        )

    def read_file(self, relative_path: str) -> CoderResult:
        try:
            content = self.workspace.read_file(relative_path)
            redacted_content, _secrets_count = self.secret_scanner.redact_secrets(content)
            return CoderResult(
                action="read_file",
                success=True,
                details=redacted_content,
                file_path=relative_path,
            )
        except Exception as exc:  # noqa: BLE001
            return CoderResult(
                action="read_file",
                success=False,
                details=f"Failed to read file '{relative_path}': {exc}",
                file_path=relative_path,
            )

    def write_file(self, relative_path: str, content: str) -> CoderResult:
        try:
            # Check if secret present in content before writing
            scan_results = self.secret_scanner.scan(content)
            if scan_results:
                return CoderResult(
                    action="write_file",
                    success=False,
                    details=f"Write blocked: content contains potential secrets ({scan_results[0]['type']}).",
                    file_path=relative_path,
                )
            self.workspace.write_file(relative_path, content)
            return CoderResult(
                action="write_file",
                success=True,
                details=f"Successfully wrote content to '{relative_path}'.",
                file_path=relative_path,
            )
        except Exception as exc:  # noqa: BLE001
            return CoderResult(
                action="write_file",
                success=False,
                details=f"Failed to write file '{relative_path}': {exc}",
                file_path=relative_path,
            )

    def apply_diff(self, relative_path: str, diff_text: str) -> CoderResult:
        try:
            scan_results = self.secret_scanner.scan(diff_text)
            if scan_results:
                return CoderResult(
                    action="apply_diff",
                    success=False,
                    details=f"Diff blocked: contains potential secrets ({scan_results[0]['type']}).",
                    file_path=relative_path,
                )
            self.workspace.apply_diff(relative_path, diff_text)
            return CoderResult(
                action="apply_diff",
                success=True,
                details=f"Successfully applied diff to '{relative_path}'.",
                file_path=relative_path,
            )
        except Exception as exc:  # noqa: BLE001
            return CoderResult(
                action="apply_diff",
                success=False,
                details=f"Failed to apply diff to '{relative_path}': {exc}",
                file_path=relative_path,
            )

    def run_tests(
        self, test_path: str = "", timeout: float = 30.0
    ) -> CoderResult:
        cmd = f"pytest {test_path}".strip()
        exec_res = self.runtime.run_command(cmd, timeout=timeout)
        success = exec_res.exit_code == 0
        details = (
            "Tests passed successfully."
            if success
            else f"Tests failed with exit code {exec_res.exit_code}."
        )
        return CoderResult(
            action="run_tests",
            success=success,
            details=details,
            execution_result=exec_res,
        )

    def execute_command(self, command: str, timeout: float = 30.0) -> CoderResult:
        exec_res = self.runtime.run_command(command, timeout=timeout)
        success = exec_res.exit_code == 0
        return CoderResult(
            action="execute_command",
            success=success,
            details=exec_res.stdout if success else exec_res.stderr,
            execution_result=exec_res,
        )
