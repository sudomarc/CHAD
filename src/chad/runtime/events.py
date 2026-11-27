"""Typed runtime event model.

Events are emitted by the loop and consumed by the TUI or persistence layer.
The TUI renders them but does not determine their meaning or policy
(docs/architecture.md: runtime events).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class EventType(str, Enum):
    USER_MESSAGE_ACCEPTED = "user_message_accepted"
    MODEL_REQUEST_STARTED = "model_request_started"
    MODEL_RESPONSE_RECEIVED = "model_response_received"
    TOOL_REQUESTED = "tool_requested"
    PERMISSION_REQUIRED = "permission_required"
    TOOL_COMPLETED = "tool_completed"
    ITERATION_COMPLETED = "iteration_completed"
    TASK_FINISHED = "task_finished"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"


@dataclass
class Event:
    type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, Any] = field(default_factory=dict)
