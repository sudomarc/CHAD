from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from chad.tools.schema import ToolDefinition


@dataclass(slots=True)
class RegisteredTool:
    definition: ToolDefinition
    handler: Callable[..., Any]


class ToolRegistry:
    """Registry for managing CHAD tools."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, definition: ToolDefinition, handler: Callable[..., Any]) -> None:
        if definition.id in self._tools:
            raise ValueError(f"Tool '{definition.id}' is already registered.")
        self._tools[definition.id] = RegisteredTool(definition=definition, handler=handler)

    def get(self, tool_id: str) -> RegisteredTool:
        if tool_id not in self._tools:
            raise KeyError(f"Tool '{tool_id}' is not registered.")
        return self._tools[tool_id]

    def list_tools(self) -> list[ToolDefinition]:
        return [tool.definition for tool in self._tools.values()]

    def is_registered(self, tool_id: str) -> bool:
        return tool_id in self._tools
