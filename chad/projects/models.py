from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class ProjectRole(StrEnum):
    OWNER = "owner"
    EDITOR = "editor"
    VIEWER = "viewer"


@dataclass(slots=True)
class ProjectMember:
    user_id: str
    role: ProjectRole = ProjectRole.VIEWER
    joined_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "role": self.role.value,
            "joined_at": self.joined_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectMember:
        return cls(
            user_id=str(data["user_id"]),
            role=ProjectRole(data.get("role", ProjectRole.VIEWER.value)),
            joined_at=str(data.get("joined_at") or datetime.now(UTC).isoformat()),
        )


@dataclass(slots=True)
class Project:
    name: str
    owner_id: str
    project_id: str = field(default_factory=lambda: str(uuid4()))
    description: str = ""
    members: dict[str, ProjectMember] = field(default_factory=dict)  # user_id -> ProjectMember
    conversation_ids: list[str] = field(default_factory=list)
    file_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def __post_init__(self) -> None:
        if self.owner_id and self.owner_id not in self.members:
            self.members[self.owner_id] = ProjectMember(
                user_id=self.owner_id,
                role=ProjectRole.OWNER,
                joined_at=self.created_at,
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "description": self.description,
            "owner_id": self.owner_id,
            "members": {uid: m.to_dict() for uid, m in self.members.items()},
            "conversation_ids": list(self.conversation_ids),
            "file_ids": list(self.file_ids),
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Project:
        raw_members = data.get("members", {})
        members = {
            uid: ProjectMember.from_dict(m_data) for uid, m_data in raw_members.items()
        }
        return cls(
            project_id=str(data["project_id"]),
            name=str(data["name"]),
            description=str(data.get("description", "")),
            owner_id=str(data["owner_id"]),
            members=members,
            conversation_ids=list(data.get("conversation_ids", [])),
            file_ids=list(data.get("file_ids", [])),
            metadata=dict(data.get("metadata", {})),
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            updated_at=str(data.get("updated_at") or datetime.now(UTC).isoformat()),
        )
