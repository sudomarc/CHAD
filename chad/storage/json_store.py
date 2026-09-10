from __future__ import annotations

import json
from pathlib import Path

from chad.core.conversation import Conversation


class ConversationStore:
    """Simple replaceable JSON persistence for local conversations."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory.expanduser()
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, conversation_id: str) -> Path:
        safe_id = "".join(char for char in conversation_id if char.isalnum() or char in "-_")
        if not safe_id:
            raise ValueError("invalid conversation id")
        return self.directory / f"{safe_id}.json"

    def save(self, conversation: Conversation) -> None:
        path = self._path(conversation.id)
        path.write_text(
            json.dumps(conversation.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def load(self, conversation_id: str) -> Conversation:
        path = self._path(conversation_id)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise KeyError(conversation_id) from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"unable to read conversation {conversation_id}") from exc
        if not isinstance(payload, dict):
            raise TypeError("conversation file must contain an object")
        return Conversation.from_dict(payload)

    def list(self) -> list[Conversation]:
        conversations: list[Conversation] = []
        for path in sorted(self.directory.glob("*.json")):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    conversations.append(Conversation.from_dict(payload))
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        return conversations
