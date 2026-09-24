from __future__ import annotations

from chad.tools.builtin import (
    CALCULATOR_TOOL,
    DATETIME_TOOL,
    FILE_READ_TOOL,
    datetime_now,
    safe_calculator,
    safe_read_file,
)
from chad.tools.executor import ToolExecutor
from chad.tools.permissions import PermissionEngine
from chad.tools.registry import RegisteredTool, ToolRegistry
from chad.tools.schema import (
    ToolAuditEvent,
    ToolDefinition,
    ToolPermissionLevel,
    ToolResult,
    ToolStatus,
)


def register_builtin_tools(registry: ToolRegistry) -> None:
    """Registers built-in tools into a ToolRegistry instance."""
    registry.register(CALCULATOR_TOOL, safe_calculator)
    registry.register(DATETIME_TOOL, datetime_now)
    registry.register(FILE_READ_TOOL, safe_read_file)


__all__ = [
    "CALCULATOR_TOOL",
    "DATETIME_TOOL",
    "FILE_READ_TOOL",
    "PermissionEngine",
    "RegisteredTool",
    "ToolAuditEvent",
    "ToolDefinition",
    "ToolExecutor",
    "ToolPermissionLevel",
    "ToolRegistry",
    "ToolResult",
    "ToolStatus",
    "datetime_now",
    "register_builtin_tools",
    "safe_calculator",
    "safe_read_file",
]
