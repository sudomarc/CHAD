from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from chad.core.messages import Message, MessageRole


class ConversationStatus(StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass(slots=True)
class Conversation:
    id: str = field(default_factory=lambda: str(uuid4()))
    title: str = "New conversation"
    system_prompt: str | None = None
    summary: str | None = None
    messages: list[Message] = field(default_factory=list)
    model: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    status: ConversationStatus = ConversationStatus.ACTIVE
    active_branch_head_id: str | None = None

    def _touch(self) -> None:
        self.updated_at = datetime.now(UTC).isoformat()

    def archive(self) -> None:
        self.status = ConversationStatus.ARCHIVED
        self._touch()

    def unarchive(self) -> None:
        self.status = ConversationStatus.ACTIVE
        self._touch()

    def soft_delete(self) -> None:
        self.status = ConversationStatus.DELETED
        self._touch()

    def restore(self) -> None:
        self.status = ConversationStatus.ACTIVE
        self._touch()

    def record_summary(self, summary: str) -> None:
        self.summary = summary
        self._touch()

    def _get_default_parent_id(self) -> str | None:
        if self.active_branch_head_id is not None:
            return self.active_branch_head_id
        if self.messages:
            return self.messages[-1].id
        return None

    def add_user(
        self,
        content: str,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Message:
        if idempotency_key is not None:
            existing = next(
                (msg for msg in self.messages if msg.idempotency_key == idempotency_key),
                None,
            )
            if existing is not None:
                return existing

        parent_id = self._get_default_parent_id()
        message = Message(
            role=MessageRole.USER,
            content=content,
            parent_id=parent_id,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )
        self.messages.append(message)
        self.active_branch_head_id = message.id
        self._touch()
        return message

    def add_assistant(
        self,
        content: str,
        correlation_id: str | None = None,
        idempotency_key: str | None = None,
    ) -> Message:
        if idempotency_key is not None:
            existing = next(
                (msg for msg in self.messages if msg.idempotency_key == idempotency_key),
                None,
            )
            if existing is not None:
                return existing

        parent_id = self._get_default_parent_id()
        message = Message(
            role=MessageRole.ASSISTANT,
            content=content,
            parent_id=parent_id,
            correlation_id=correlation_id,
            idempotency_key=idempotency_key,
        )
        self.messages.append(message)
        self.active_branch_head_id = message.id
        self._touch()
        return message

    def get_active_messages(self) -> list[Message]:
        if not self.messages:
            return []

        msg_map = {msg.id: msg for msg in self.messages}

        # Determine head
        head_id = self.active_branch_head_id
        if head_id is None or head_id not in msg_map:
            head_id = self.messages[-1].id

        # Trace back using parent_id links
        branch: list[Message] = []
        curr_id: str | None = head_id
        visited: set[str] = set()

        while curr_id is not None and curr_id in msg_map:
            if curr_id in visited:
                break
            visited.add(curr_id)
            msg = msg_map[curr_id]
            branch.append(msg)
            curr_id = msg.parent_id

        # If no parent linkages were present in legacy messages, fallback to simple slice
        if len(branch) == 1 and branch[0].parent_id is None and len(self.messages) > 1:
            idx = self.messages.index(branch[0])
            if idx > 0 and all(m.parent_id is None for m in self.messages):
                return self.messages[: idx + 1]

        branch.reverse()
        return branch

    def edit_message(self, message_id: str, new_content: str) -> Message:
        target = next((msg for msg in self.messages if msg.id == message_id), None)
        if target is None:
            raise KeyError(f"Message {message_id} not found in conversation")

        edited_msg = Message(
            role=target.role,
            content=new_content,
            parent_id=target.parent_id,
            edited_from_id=target.id,
            images=target.images,
        )
        self.messages.append(edited_msg)
        self.active_branch_head_id = edited_msg.id
        self._touch()
        return edited_msg

    def regenerate_message(self, message_id: str) -> Message | None:
        target = next((msg for msg in self.messages if msg.id == message_id), None)
        if target is None:
            raise KeyError(f"Message {message_id} not found in conversation")

        if target.role == MessageRole.ASSISTANT:
            # Set head to parent user message to regenerate response
            if target.parent_id is not None:
                self.switch_branch(target.parent_id)
                parent_msg = next((msg for msg in self.messages if msg.id == target.parent_id), None)
                return parent_msg
        else:
            self.switch_branch(target.id)
            return target
        return None

    def switch_branch(self, message_id: str) -> None:
        if not any(msg.id == message_id for msg in self.messages):
            raise KeyError(f"Message {message_id} not found in conversation")
        self.active_branch_head_id = message_id
        self._touch()

    def clear(self) -> None:
        self.messages.clear()
        self.active_branch_head_id = None
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

        active_history = self.get_active_messages()
        history = active_history if max_messages is None else active_history[-max_messages:]
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
            "summary": self.summary,
            "model": self.model,
            "status": self.status.value,
            "active_branch_head_id": self.active_branch_head_id,
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

        raw_status = data.get("status", "active")
        status = (
            ConversationStatus(str(raw_status))
            if raw_status in (s.value for s in ConversationStatus)
            else ConversationStatus.ACTIVE
        )

        active_head = data.get("active_branch_head_id")
        summary = data.get("summary")

        return cls(
            id=str(data.get("id") or uuid4()),
            title=str(data.get("title") or "New conversation"),
            system_prompt=data.get("system_prompt")
            if isinstance(data.get("system_prompt"), str)
            else None,
            summary=str(summary) if isinstance(summary, str) else None,
            model=data.get("model") if isinstance(data.get("model"), str) else None,
            status=status,
            active_branch_head_id=str(active_head) if isinstance(active_head, str) else None,
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
    correlation_id: str | None = None
    idempotency_key: str | None = None

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
