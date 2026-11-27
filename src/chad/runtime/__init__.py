"""CHAD agent runtime (M2).

Coordinates a task from user request to verified outcome: state transitions,
model calls, tool dispatch, budgets, cancellation, and reporting.

The runtime is provider- and TUI-agnostic. Providers and tools are injected
through protocols so they can be faked in tests and swapped in production.

Note: provider-backed names (``AgentLoop``, ``ModelResponse``...) are
imported lazily to avoid an import cycle with ``chad.gateway``, whose
contract module imports only the pure ``chad.runtime.contracts`` data
module.
"""

from __future__ import annotations

from .contracts import Message, Role, ToolCall, ToolResult, new_id
from .events import Event, EventType
from .task import Task, TaskStatus, TransitionError

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
    "ToolCall",
    "ToolResult",
    "TransitionError",
    "new_id",
]


def __getattr__(name: str):
    if name in ("AgentLoop", "LoopLimits", "TaskReport"):
        from .loop import AgentLoop, LoopLimits, TaskReport

        return {"AgentLoop": AgentLoop, "LoopLimits": LoopLimits, "TaskReport": TaskReport}[name]
    if name in ("ModelResponse", "Provider"):
        from .provider import ModelResponse, Provider

        return {"ModelResponse": ModelResponse, "Provider": Provider}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
