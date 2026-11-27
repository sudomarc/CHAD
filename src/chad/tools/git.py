"""Git inspection tools (issue #74)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from chad.runtime.contracts import ToolResult

from .base import BaseTool, ToolSpec


def _run_git(workspace: Path, args: list[str]) -> tuple[str, str | None]:
    """Run a git command inside the workspace; return (output, error)."""
    try:
        proc = subprocess.run(
            ["git", *args],
            cwd=str(workspace),
            capture_output=True,
            check=False,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        if isinstance(exc, FileNotFoundError):
            return "", "git command not found"
        return "", "git command timed out"
    if proc.returncode != 0:
        err = (proc.stderr or "").strip() or f"git exited with code {proc.returncode}"
        return "", err
    return (proc.stdout or ""), None


class GitStatusTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="git_status",
                description="Show the working-tree git status.",
                input_schema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
                risk="read",
                permission="read-only",
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        output, error = _run_git(self.workspace, ["status", "--porcelain"])
        if error:
            return ToolResult(tool_call_id="", name=self.name, error=error)
        return ToolResult(
            tool_call_id="",
            name=self.name,
            output=output.strip() or "(working tree clean)",
        )


class GitDiffTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="git_diff",
                description="Show the working-tree diff.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Optional path to limit the diff to.",
                        }
                    },
                    "required": [],
                },
                risk="read",
                permission="read-only",
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        args = ["diff"]
        if arguments.get("path"):
            args.append("--")
            args.append(arguments["path"])
        output, error = _run_git(self.workspace, args)
        if error:
            return ToolResult(tool_call_id="", name=self.name, error=error)
        return ToolResult(
            tool_call_id="", name=self.name, output=output.strip() or "(no changes)"
        )


class GitLogTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="git_log",
                description="Show recent commit history.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Max number of commits (default 20).",
                        }
                    },
                    "required": [],
                },
                risk="read",
                permission="read-only",
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        limit = int(arguments.get("limit", 20))
        output, error = _run_git(
            self.workspace, ["log", "--oneline", f"-n{limit}"]
        )
        if error:
            return ToolResult(tool_call_id="", name=self.name, error=error)
        return ToolResult(
            tool_call_id="", name=self.name, output=output.strip() or "(no commits)"
        )
