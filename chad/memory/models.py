from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    WORKING = "working"
    CONVERSATION = "conversation"
    USER = "user"
    PROJECT = "project"
    SEMANTIC = "semantic"


class MemoryScope(str, Enum):
    GLOBAL = "global"
    USER = "user"
    PROJECT = "project"
    SESSION = "session"


@dataclass
class MemoryItem:
    key: str
    content: str
    memory_type: MemoryType = MemoryType.WORKING
    scope: MemoryScope = MemoryScope.SESSION
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str | None = None
    project_id: str | None = None
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    approved: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "key": self.key,
            "content": self.content,
            "memory_type": self.memory_type.value if isinstance(self.memory_type, Enum) else self.memory_type,
            "scope": self.scope.value if isinstance(self.scope, Enum) else self.scope,
            "user_id": self.user_id,
            "project_id": self.project_id,
            "session_id": self.session_id,
            "metadata": self.metadata,
            "confidence": self.confidence,
            "approved": self.approved,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MemoryItem:
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            key=data["key"],
            content=data["content"],
            memory_type=MemoryType(data.get("memory_type", MemoryType.WORKING)),
            scope=MemoryScope(data.get("scope", MemoryScope.SESSION)),
            user_id=data.get("user_id"),
            project_id=data.get("project_id"),
            session_id=data.get("session_id"),
            metadata=data.get("metadata", {}),
            confidence=data.get("confidence", 1.0),
            approved=data.get("approved", True),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )


@dataclass
class MemoryConflict:
    existing_memory: MemoryItem
    new_memory: MemoryItem
    reason: str
    conflict_type: str = "contradiction"  # e.g. "contradiction", "update"
