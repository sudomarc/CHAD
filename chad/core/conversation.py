from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import math
from uuid import uuid4

from chad.core.messages import Message, MessageRole


@dataclass(slots=True)
class Conversation:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = "New conversation"
    system_prompt: str | None = None
    messages: list[Message] = field(default_factory=list)
    model: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()

    def add_user(self, content: str) -> Message:
        message = Message(MessageRole.USER, content)
        self.messages.append(message)
        self._touch()
        return message

    def add_assistant(self, content: str) -> Message:
        message = Message(MessageRole.ASSISTANT, content)
        self.messages.append(message)
        self._touch()
        return message

    def clear(self) -> None:
        self.messages.clear()
        self._touch()

    def context(
        self,
        max_messages: int | None = None,
        max_input_tokens: int | None = None,
    ) -> list[Message]:
        if max_messages is not None and max_messages < 1:
            raise ValueError("max_messages must be at least 1")
        ordered: list[Message] = []
        if self.system_prompt and self.system_prompt.strip():
            ordered.append(Message(MessageRole.SYSTEM, self.system_prompt.strip()))

        history = self.messages if max_messages is None else self.messages[-max_messages:]
        ordered.extend(history)

        if max_input_tokens is not None:
            from chad.core.context import ContextBudget

            ordered = ContextBudget(max_input_tokens).trim(ordered)
        return ordered

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "title": self.title,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": [message.to_dict() for message in self.messages],
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Conversation:
        raw_messages = data.get("messages", [])
        if not isinstance(raw_messages, list):
            raise TypeError("conversation messages must be a list")
        if any(not isinstance(item, dict) for item in raw_messages):
            raise TypeError("conversation messages must contain objects")
        return cls(
            id=str(data.get("id") or uuid4()),
            title=str(data.get("title") or "New conversation"),
            system_prompt=data.get("system_prompt")
            if isinstance(data.get("system_prompt"), str)
            else None,
            model=data.get("model") if isinstance(data.get("model"), str) else None,
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(UTC).isoformat()),
            messages=[Message.from_dict(item) for item in raw_messages],
        )


@dataclass(frozen=True, slots=True)
class ChatRequest:
    messages: tuple[Message, ...]
    model: str | None = None
    max_new_tokens: int = 128
    temperature: float = 0.8
    top_k: int = 40
    top_p: float = 0.95

    def validate(self) -> None:
        if not self.messages:
            raise ValueError("chat request must contain at least one message")
        if self.max_new_tokens < 1:
            raise ValueError("max_new_tokens must be at least 1")
        if self.top_k < 0:
            raise ValueError("top_k must be >= 0")
        if not math.isfinite(self.temperature) or self.temperature <= 0:
            raise ValueError("temperature must be finite and greater than 0")
        if not math.isfinite(self.top_p) or not 0 < self.top_p <= 1:
            raise ValueError("top_p must be finite and in the range (0, 1]")
