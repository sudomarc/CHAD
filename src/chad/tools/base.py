"""Base tool implementation with workspace-boundary enforcement.

Concrete tools subclass ``BaseTool`` and implement ``_run``. File paths are
resolved canonically and must stay within the configured workspace;
traversal, symlink escapes, and paths outside the root are rejected
(docs/tools-and-permissions.md: workspace boundaries).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from chad.runtime.contracts import ToolResult
from chad.runtime.tools import ToolSchema


class WorkspaceEscape(Exception):
    """Raised when a path resolves outside the configured workspace."""


def resolve_within(workspace: str | Path, *parts: str) -> Path:
    """Resolve ``parts`` relative to ``workspace``.

    Rejects ``..`` traversal and symlink escapes that land outside the
    workspace root. Re-checked at execution time (boundary is re-resolved
    on every call).
    """
    root = Path(workspace).resolve()
    target = (root / Path(*parts)).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise WorkspaceEscape(f"path escapes workspace: {target}") from exc
    return target


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    risk: str  # "read" | "write" | "execute" | "dangerous"
    permission: str  # "read-only" | "ask" | "policy-authorized"
    timeout_seconds: int = 30


def validate_arguments(
    schema: dict[str, Any], arguments: dict[str, Any]
) -> list[str]:
    """Lightweight JSON-schema validation subset. Returns error messages."""
    errors: list[str] = []
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    for key in required:
        if key not in arguments:
            errors.append(f"missing required argument: {key}")
    for key, value in arguments.items():
        if key not in properties:
            errors.append(f"unknown argument: {key}")
            continue
        expected = properties[key].get("type")
        if expected == "string" and not isinstance(value, str):
            errors.append(f"argument {key} must be a string")
        elif expected == "integer" and not isinstance(value, int):
            errors.append(f"argument {key} must be an integer")
        elif expected == "boolean" and not isinstance(value, bool):
            errors.append(f"argument {key} must be a boolean")
        elif expected == "array" and not isinstance(value, list):
            errors.append(f"argument {key} must be an array")
    return errors


class BaseTool:
    def __init__(self, spec: ToolSpec) -> None:
        self.spec = spec

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def description(self) -> str:
        return self.spec.description

    @property
    def input_schema(self) -> dict[str, Any]:
        return self.spec.input_schema

    def schema(self) -> ToolSchema:
        return ToolSchema(
            name=self.spec.name,
            description=self.spec.description,
            input_schema=self.spec.input_schema,
        )

    def call(self, arguments: dict[str, Any]) -> ToolResult:
        errors = validate_arguments(self.spec.input_schema, arguments)
        if errors:
            return ToolResult(
                tool_call_id="", name=self.name, error="; ".join(errors)
            )
        try:
            return self._run(arguments)
        except WorkspaceEscape as exc:
            return ToolResult(tool_call_id="", name=self.name, error=str(exc))
        except Exception as exc:  # noqa: BLE001 - surface tool failure cleanly
            return ToolResult(
                tool_call_id="", name=self.name, error=f"{self.name} failed: {exc}"
            )

    def _run(self, arguments: dict[str, Any]) -> ToolResult:
        raise NotImplementedError
