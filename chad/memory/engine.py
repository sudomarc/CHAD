from __future__ import annotations

import time
from typing import Any

from chad.memory.models import MemoryConflict, MemoryItem, MemoryScope, MemoryType
from chad.memory.store import MemoryStore


class MemoryEngine:
    """High-level orchestration engine for memory operations across scopes and types."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store if store is not None else MemoryStore()

    def add_working_memory(
        self,
        key: str,
        content: str,
        session_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        item = MemoryItem(
            key=key,
            content=content,
            memory_type=MemoryType.WORKING,
            scope=MemoryScope.SESSION,
            session_id=session_id,
            metadata=metadata or {},
        )
        return self.store.add(item)

    def add_user_preference(
        self,
        key: str,
        content: str,
        user_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> tuple[MemoryItem, MemoryConflict | None]:
        existing = self.store.get_by_key(key=key, scope=MemoryScope.USER, user_id=user_id)
        conflict: MemoryConflict | None = None

        new_item = MemoryItem(
            key=key,
            content=content,
            memory_type=MemoryType.USER,
            scope=MemoryScope.USER,
            user_id=user_id,
            metadata=metadata or {},
        )

        if existing:
            if existing.content != content:
                conflict = MemoryConflict(
                    existing_memory=existing,
                    new_memory=new_item,
                    reason=f"User preference for '{key}' changed from '{existing.content}' to '{content}'",
                    conflict_type="update",
                )
            self.store.update(existing.id, content=content, metadata=metadata)
            return existing, conflict

        added = self.store.add(new_item)
        return added, None

    def add_project_memory(
        self,
        key: str,
        content: str,
        project_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> MemoryItem:
        existing = self.store.get_by_key(key=key, scope=MemoryScope.PROJECT, project_id=project_id)
        if existing:
            self.store.update(existing.id, content=content, metadata=metadata)
            return existing

        item = MemoryItem(
            key=key,
            content=content,
            memory_type=MemoryType.PROJECT,
            scope=MemoryScope.PROJECT,
            project_id=project_id,
            metadata=metadata or {},
        )
        return self.store.add(item)

    def record_conversation_summary(
        self,
        session_id: str,
        summary: str,
        message_count: int,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> MemoryItem:
        key = f"summary:{session_id}"
        existing = self.store.get_by_key(key=key, scope=MemoryScope.SESSION, session_id=session_id)

        meta = {"message_count": message_count, "last_summarized_at": time.time()}
        if existing:
            self.store.update(existing.id, content=summary, metadata=meta)
            return existing

        item = MemoryItem(
            key=key,
            content=summary,
            memory_type=MemoryType.CONVERSATION,
            scope=MemoryScope.SESSION,
            session_id=session_id,
            user_id=user_id,
            project_id=project_id,
            metadata=meta,
        )
        return self.store.add(item)

    def search_memories(
        self,
        query: str,
        user_id: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
        memory_types: list[MemoryType] | None = None,
        top_k: int = 5,
    ) -> list[tuple[MemoryItem, float]]:
        """Keyword and semantic scoring over accessible memories."""
        query_terms = set(query.lower().split())
        candidates: list[MemoryItem] = []

        # Gather relevant items
        all_items = self.store.list(approved_only=True)
        for item in all_items:
            # Check scope/ownership accessibility
            if item.user_id and user_id and item.user_id != user_id:
                continue
            if item.project_id and project_id and item.project_id != project_id:
                continue
            if item.session_id and session_id and item.session_id != session_id:
                continue
            if memory_types and item.memory_type not in memory_types:
                continue
            candidates.append(item)

        scored: list[tuple[MemoryItem, float]] = []
        for item in candidates:
            item_text = f"{item.key} {item.content}".lower()
            item_terms = set(item_text.split())

            if not query_terms or not item_terms:
                score = 0.0
            else:
                intersection = query_terms.intersection(item_terms)
                score = len(intersection) / float(len(query_terms))

            if score > 0:
                scored.append((item, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]
