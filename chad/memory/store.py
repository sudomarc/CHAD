from __future__ import annotations

import json
import time
from typing import Any

from chad.memory.models import MemoryItem, MemoryScope, MemoryType


class MemoryStore:
    """In-memory or persistent store for memory items with CRUD, search, and export capabilities."""

    def __init__(self) -> None:
        self._memories: dict[str, MemoryItem] = {}

    def add(self, item: MemoryItem) -> MemoryItem:
        self._memories[item.id] = item
        return item

    def get(self, memory_id: str) -> MemoryItem | None:
        return self._memories.get(memory_id)

    def get_by_key(
        self,
        key: str,
        scope: MemoryScope | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> MemoryItem | None:
        for item in self._memories.values():
            if item.key == key:
                if scope and item.scope != scope:
                    continue
                if user_id and item.user_id != user_id:
                    continue
                if project_id and item.project_id != project_id:
                    continue
                if session_id and item.session_id != session_id:
                    continue
                return item
        return None

    def list(
        self,
        memory_type: MemoryType | None = None,
        scope: MemoryScope | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
        approved_only: bool = False,
    ) -> list[MemoryItem]:
        results: list[MemoryItem] = []
        for item in self._memories.values():
            if memory_type and item.memory_type != memory_type:
                continue
            if scope and item.scope != scope:
                continue
            if user_id and item.user_id != user_id:
                continue
            if project_id and item.project_id != project_id:
                continue
            if session_id and item.session_id != session_id:
                continue
            if approved_only and not item.approved:
                continue
            results.append(item)
        return results

    def update(
        self,
        memory_id: str,
        content: str | None = None,
        metadata: dict[str, Any] | None = None,
        approved: bool | None = None,
        confidence: float | None = None,
    ) -> MemoryItem | None:
        item = self.get(memory_id)
        if not item:
            return None
        if content is not None:
            item.content = content
        if metadata is not None:
            item.metadata.update(metadata)
        if approved is not None:
            item.approved = approved
        if confidence is not None:
            item.confidence = confidence
        item.updated_at = time.time()
        return item

    def delete(self, memory_id: str) -> bool:
        if memory_id in self._memories:
            del self._memories[memory_id]
            return True
        return False

    def clear_scope(
        self,
        scope: MemoryScope,
        user_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
    ) -> int:
        to_delete = [
            item.id
            for item in self.list(
                scope=scope,
                user_id=user_id,
                project_id=project_id,
                session_id=session_id,
            )
        ]
        for memory_id in to_delete:
            self.delete(memory_id)
        return len(to_delete)

    def export_json(
        self,
        scope: MemoryScope | None = None,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> str:
        items = self.list(scope=scope, user_id=user_id, project_id=project_id)
        return json.dumps([item.to_dict() for item in items], indent=2)

    def import_json(self, json_str: str) -> list[MemoryItem]:
        data = json.loads(json_str)
        imported: list[MemoryItem] = []
        for entry in data:
            item = MemoryItem.from_dict(entry)
            self.add(item)
            imported.append(item)
        return imported
