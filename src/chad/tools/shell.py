"""Controlled terminal process execution (issue #73).

Commands are executed as an argument array (never a shell string) with an
explicit working directory, bounded timeout, and bounded output.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from chad.runtime.contracts import ToolResult

from .base import BaseTool, ToolSpec, resolve_within

MAX_OUTPUT_BYTES = 200_000


class ShellTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="shell",
                description="Execute a command within the workspace.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Command and arguments (no shell).",
                        },
                        "cwd": {
                            "type": "string",
                            "description": "Working directory relative to the workspace.",
                        },
                        "timeout": {
                            "type": "integer",
                            "description": "Timeout in seconds (default 30).",
                        },
                    },
                    "required": ["command"],
                },
                risk="execute",
                permission="ask",
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        command = arguments["command"]
        cwd = resolve_within(self.workspace, arguments.get("cwd", "."))
        timeout = int(arguments.get("timeout", 30))

        try:
            proc = subprocess.run(
                command,
                cwd=str(cwd),
                capture_output=True,
                check=False,
                text=True,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            out = str(exc.stdout or "") + "\n[command timed out]"
            return ToolResult(
                tool_call_id="",
                name=self.name,
                output=out[:MAX_OUTPUT_BYTES],
                error=f"timed out after {timeout}s",
            )

        output = str(proc.stdout or "")
        if proc.stderr:
            output += "\nSTDERR:\n" + str(proc.stderr or "")
        result: ToolResult | None = None
        if proc.returncode != 0:
            result = ToolResult(
                tool_call_id="",
                name=self.name,
                output=output[:MAX_OUTPUT_BYTES],
                error=f"exit code {proc.returncode}",
            )
        else:
            result = ToolResult(
                tool_call_id="", name=self.name, output=output[:MAX_OUTPUT_BYTES]
            )
        return result
