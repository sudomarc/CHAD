"""Safe file creation and editing with reviewable diffs (issue #79)."""

from __future__ import annotations

import difflib
from pathlib import Path
from typing import Any

from chad.runtime.contracts import ToolResult

from .base import BaseTool, ToolSpec, resolve_within


class EditTool(BaseTool):
    def __init__(self, workspace: str | Path) -> None:
        super().__init__(
            ToolSpec(
                name="edit",
                description="Create or edit a file with a reviewable unified diff.",
                input_schema={
                    "type": "object",
                    "properties": {
                        "operation": {
                            "type": "string",
                            "enum": ["create", "edit"],
                            "description": "create a new file, or str_replace in an existing file",
                        },
                        "path": {
                            "type": "string",
                            "description": "Path to the file, relative to the workspace.",
                        },
                        "old_string": {
                            "type": "string",
                            "description": "Text to replace (required for edit).",
                        },
                        "new_string": {
                            "type": "string",
                            "description": "Replacement text (for create: file contents).",
                        },
                    },
                    "required": ["operation", "path"],
                },
                risk="write",
                permission="ask",
                timeout_seconds=30,
            )
        )
        self.workspace = Path(workspace)

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        operation = arguments["operation"]
        rel_path = arguments["path"]
        path = resolve_within(self.workspace, rel_path)

        if operation == "create":
            if path.exists():
                return ToolResult(
                    tool_call_id="",
                    name=self.name,
                    error=f"file already exists: {rel_path}",
                )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(arguments.get("new_string", ""), encoding="utf-8")
            return ToolResult(
                tool_call_id="", name=self.name, output=f"created {rel_path}"
            )

        if operation == "edit":
            if not path.is_file():
                return ToolResult(
                    tool_call_id="", name=self.name, error=f"not a file: {rel_path}"
                )
            old_string = arguments.get("old_string", "")
            new_string = arguments.get("new_string", "")
            before = path.read_text(encoding="utf-8")
            if old_string not in before:
                return ToolResult(
                    tool_call_id="",
                    name=self.name,
                    error="old_string not found in file",
                )
            after = before.replace(old_string, new_string, 1)
            path.write_text(after, encoding="utf-8")
            diff = self._unified_diff(rel_path, before, after)
            return ToolResult(
                tool_call_id="",
                name=self.name,
                output=f"edited {rel_path}\n{diff}",
            )

        return ToolResult(
            tool_call_id="", name=self.name, error=f"unknown operation: {operation}"
        )

    @staticmethod
    def _unified_diff(name: str, before: str, after: str) -> str:
        lines = [f"--- a/{name}", f"+++ b/{name}"]
        lines.extend(
            difflib.unified_diff(before.splitlines(), after.splitlines(), lineterm="")
        )
        return "\n".join(lines)
