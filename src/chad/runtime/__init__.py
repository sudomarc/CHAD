"""CHAD agent runtime (M2).

Coordinates a task from user request to verified outcome: state transitions,
model calls, tool dispatch, budgets, cancellation, and reporting.

The runtime is provider- and TUI-agnostic. Providers and tools are injected
through protocols so they can be faked in tests and swapped in production.
"""

from .contracts import Message, Role, ToolCall, ToolResult
from .events import Event, EventType
from .loop import AgentLoop, LoopLimits, TaskReport
from .provider import ModelResponse, Provider
from .task import Task, TaskStatus, TransitionError
from .tools import Tool, ToolError, ToolRegistry

__all__ = [
    "AgentLoop",
    "Event",
    "EventType",
    "LoopLimits",
    "Message",
    "ModelResponse",
    "Provider",
    "Role",
    "Task",
    "TaskReport",
    "TaskStatus",
    "Tool",
    "ToolCall",
    "ToolError",
    "ToolRegistry",
    "ToolResult",
    "TransitionError",
]
