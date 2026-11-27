"""Task state machine for the agent runtime.

A task can be pending, running, waiting_for_permission, completed, failed,
or cancelled. Invalid transitions are rejected. A failed tool call is data
for the next reasoning step; it is never silently converted to success
(docs/agent-runtime.md: state model).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Final

from .contracts import Message, ToolResult


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_PERMISSION = "waiting_for_permission"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_TERMINAL: Final[frozenset[TaskStatus]] = frozenset(
    {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
)

_VALID_TRANSITIONS: Final[dict[TaskStatus, frozenset[TaskStatus]]] = {
    TaskStatus.PENDING: frozenset({TaskStatus.RUNNING}),
    TaskStatus.RUNNING: frozenset(
        {
            TaskStatus.WAITING_FOR_PERMISSION,
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }
    ),
    TaskStatus.WAITING_FOR_PERMISSION: frozenset(
        {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.FAILED}
    ),
}


class TransitionError(Exception):
    """Raised when a task status transition is not permitted."""


@dataclass
class Task:
    id: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    messages: list[Message] = field(default_factory=list)
    results: list[ToolResult] = field(default_factory=list)
    error: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def is_terminal(self) -> bool:
        return self.status in _TERMINAL

    def transition(self, new_status: TaskStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(self.status, frozenset())
        if new_status not in allowed:
            raise TransitionError(
                f"invalid transition {self.status.value} -> {new_status.value}"
            )
        self.status = new_status
        self.updated_at = datetime.now(UTC)
