from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum


class MessageRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass(frozen=True, slots=True)
class Message:
    role: MessageRole
    content: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self) -> None:
        if not self.content.strip():
            raise ValueError("message content must not be empty")

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role.value, "content": self.content, "created_at": self.created_at}

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "Message":
        return cls(
            role=MessageRole(data["role"]),
            content=data["content"],
            created_at=data.get("created_at") or datetime.now(timezone.utc).isoformat(),
        )
