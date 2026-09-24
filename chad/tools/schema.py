from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ToolPermissionLevel(StrEnum):
    ALWAYS_ALLOW = "ALWAYS_ALLOW"
    USER_APPROVAL = "USER_APPROVAL"
    ADMIN_ONLY = "ADMIN_ONLY"
    BLOCKED = "BLOCKED"


class ToolStatus(StrEnum):
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    TIMEOUT = "TIMEOUT"
    PERMISSION_DENIED = "PERMISSION_DENIED"


@dataclass(frozen=True, slots=True)
class ToolDefinition:
    id: str
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] = field(default_factory=dict)
    permission_level: ToolPermissionLevel = ToolPermissionLevel.ALWAYS_ALLOW
    timeout_seconds: float = 30.0
    side_effect_level: str = "READ_ONLY"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "permission_level": self.permission_level.value,
            "timeout_seconds": self.timeout_seconds,
            "side_effect_level": self.side_effect_level,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ToolDefinition:
        return cls(
            id=str(data["id"]),
            name=str(data["name"]),
            description=str(data["description"]),
            input_schema=dict(data.get("input_schema", {})),
            output_schema=dict(data.get("output_schema", {})),
            permission_level=ToolPermissionLevel(
                data.get("permission_level", ToolPermissionLevel.ALWAYS_ALLOW.value)
            ),
            timeout_seconds=float(data.get("timeout_seconds", 30.0)),
            side_effect_level=str(data.get("side_effect_level", "READ_ONLY")),
        )


@dataclass(frozen=True, slots=True)
class ToolResult:
    tool_id: str
    status: ToolStatus
    output: Any | None = None
    error: str | None = None
    execution_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "status": self.status.value,
            "output": self.output,
            "error": self.error,
            "execution_time_seconds": self.execution_time_seconds,
        }


@dataclass(frozen=True, slots=True)
class ToolAuditEvent:
    tool_id: str
    action: str
    status: ToolStatus
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    input_payload: dict[str, Any] = field(default_factory=dict)
    output_payload: Any | None = None
    error_message: str | None = None
    user_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_id": self.tool_id,
            "action": self.action,
            "status": self.status.value,
            "timestamp": self.timestamp,
            "input_payload": self.input_payload,
            "output_payload": self.output_payload,
            "error_message": self.error_message,
            "user_id": self.user_id,
        }
