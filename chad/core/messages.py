from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class Message:
    role: MessageRole
    content: str
    id: str = field(default_factory=lambda: str(uuid4()))
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("message content must not be empty")
        if not self.id.strip():
            raise ValueError("message id must not be empty")

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "role": self.role.value,
            "content": self.content,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Message:
        if not isinstance(data.get("role"), str):
            raise TypeError("message role must be a string")
        if not isinstance(data.get("content"), str):
            raise TypeError("message content must be a string")
        return cls(
            id=str(data.get("id") or uuid4()),
            role=MessageRole(data["role"]),
            content=data["content"],
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
        )
