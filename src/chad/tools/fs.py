"""Workspace-bound filesystem tools (M4 / issues #71, #79)."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from chad.runtime.contracts import ToolResult

from .base import BaseTool, ToolSpec, resolve_within


class ReadTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="read",
                description="Read a file within the workspace.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Path to the file, relative to the workspace.",
                        }
                    },
                    "required": ["path"],
                },
                risk="read",
                permission="read-only",
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        path = resolve_within(self.workspace, arguments["path"])
        if not path.is_file():
            return ToolResult(
                tool_call_id="", name=self.name, error=f"not a file: {arguments['path']}"
            )
        content = path.read_text(encoding="utf-8")
        return ToolResult(tool_call_id="", name=self.name, output=content)


class ListTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="list",
                description="List entries of a directory within the workspace.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory to list, relative to the workspace.",
                        }
                    },
                    "required": ["path"],
                },
                risk="read",
                permission="read-only",
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        path = resolve_within(self.workspace, arguments["path"])
        if not path.is_dir():
            return ToolResult(
                tool_call_id="",
                name=self.name,
                error=f"not a directory: {arguments['path']}",
            )
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name))
        lines = [entry.name + ("/" if entry.is_dir() else "") for entry in entries]
        return ToolResult(
            tool_call_id="", name=self.name, output="\n".join(lines) or "(empty)"
        )


class GrepTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="grep",
                description="Search file contents within the workspace.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Regular expression to search for.",
                        },
                        "path": {
                            "type": "string",
                            "description": "File or directory to search (default: workspace root).",
                        },
                    },
                    "required": ["pattern"],
                },
                risk="read",
                permission="read-only",
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        pattern = arguments["pattern"]
        root = resolve_within(self.workspace, arguments.get("path", "."))
        rx = re.compile(pattern)
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        matches: list[str] = []
        for file in files:
            if not file.is_file():
                continue
            try:
                text = file.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for lineno, line in enumerate(text.splitlines(), 1):
                if rx.search(line):
                    matches.append(
                        f"{file.relative_to(self.workspace)}:{lineno}:{line}"
                    )
        if not matches:
            return ToolResult(tool_call_id="", name=self.name, output="(no matches)")
        return ToolResult(
            tool_call_id="", name=self.name, output="\n".join(matches[:200])
        )


class GlobTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="glob",
                description="Find files by name pattern within the workspace.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "pattern": {
                            "type": "string",
                            "description": "Glob pattern (e.g. **/*.py).",
                        }
                    },
                    "required": ["pattern"],
                },
                risk="read",
                permission="read-only",
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        root = Path(self.workspace).resolve()
        matches = sorted(
            str(p.relative_to(root).as_posix())
            for p in root.rglob(arguments["pattern"])
            if p.is_file()
        )
        if not matches:
            return ToolResult(tool_call_id="", name=self.name, output="(no matches)")
        return ToolResult(tool_call_id="", name=self.name, output="\n".join(matches))
