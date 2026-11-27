"""Typed domain contracts for the agent runtime.

Pure data structures exchanged between the loop, providers, tools, and
policy. No behavior; standard library only.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


def new_id(prefix: str = "msg") -> str:
    return f"{prefix}-{uuid4().hex[:12]}"


class Role(str, Enum):
    """Closed set of message roles; unknown roles are rejected by the loop."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass(frozen=True)
class Message:
    role: Role
    content: str
    tool_calls: tuple[ToolCall, ...] = field(default_factory=tuple)
    tool_call_id: str | None = None
    id: str = field(default_factory=lambda: new_id("msg"))


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ToolResult:
    tool_call_id: str
    name: str
    output: str | None = None
    error: str | None = None
    id: str = field(default_factory=lambda: new_id("result"))

    @property
    def is_error(self) -> bool:
        return self.error is not None
