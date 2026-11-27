"""Tool system: protocol, registry, and schemas.

Every tool declares a stable identifier, purpose, validated input schema,
structured output, risk classification, timeout, and permission requirement
(docs/tools-and-permissions.md).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .contracts import ToolResult


@dataclass(frozen=True)
class ToolSchema:
    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)


class ToolError(Exception):
    """Raised when a tool cannot be executed (validation, policy, failure)."""


@runtime_checkable
class Tool(Protocol):
    name: str

    def call(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the tool with validated arguments; return a ToolResult.

        Never simulate success: on failure return a ToolResult with ``error``
        set (or raise ToolError, which the loop converts to an error result).
        """
        ...


class ToolRegistry:
    """Registers tools and exposes their schemas for provider requests."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def schemas(self) -> tuple[ToolSchema, ...]:
        return tuple(
            ToolSchema(
                name=tool.name,
                description=getattr(tool, "description", ""),
                input_schema=getattr(tool, "input_schema", {}),
            )
            for tool in self._tools.values()
        )
