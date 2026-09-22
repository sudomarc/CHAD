from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from chad.core.conversation import Conversation


class ConversationStore:
    """Replaceable local persistence with atomic conversation writes."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory.expanduser()
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path(self, conversation_id: str) -> Path:
        if (
            not conversation_id
            or not all(char.isalnum() or char in "-_" for char in conversation_id)
        ):
            raise ValueError("invalid conversation id")
        return self.directory / f"{conversation_id}.json"

    def save(self, conversation: Conversation) -> None:
        path = self._path(conversation.id)
        payload = json.dumps(
            conversation.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=self.directory,
            prefix=f".{path.stem}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(payload)
            temp_path = Path(temporary.name)

        try:
            os.replace(temp_path, path)
        finally:
            temp_path.unlink(missing_ok=True)

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
        for path in sorted(
            self.directory.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        ):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict):
                    conversations.append(Conversation.from_dict(payload))
            except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
                continue
        return conversations
