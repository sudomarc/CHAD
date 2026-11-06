from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any


class UserRole(str, Enum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class Permission(str, Enum):
    # Conversations
    CONVERSATION_CREATE = "conversation:create"
    CONVERSATION_READ = "conversation:read"
    CONVERSATION_DELETE = "conversation:delete"
    CONVERSATION_SHARE = "conversation:share"

    # Agent / Execution
    RUN_EXECUTE = "run:execute"
    RUN_CANCEL = "run:cancel"

    # Tools & Connectors
    TOOL_USE = "tool:use"
    CONNECTOR_USE = "connector:use"
    CONNECTOR_ADMIN = "connector:admin"

    # Memory
    MEMORY_READ = "memory:read"
    MEMORY_WRITE = "memory:write"
    MEMORY_DELETE = "memory:delete"

    # Admin / System
    USER_MANAGE = "user:manage"
    AUDIT_READ = "audit:read"
    SYSTEM_CONFIG = "system:config"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: set(Permission),
    UserRole.MEMBER: {
        Permission.CONVERSATION_CREATE,
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_DELETE,
        Permission.CONVERSATION_SHARE,
        Permission.RUN_EXECUTE,
        Permission.RUN_CANCEL,
        Permission.TOOL_USE,
        Permission.CONNECTOR_USE,
        Permission.MEMORY_READ,
        Permission.MEMORY_WRITE,
        Permission.MEMORY_DELETE,
    },
    UserRole.GUEST: {
        Permission.CONVERSATION_CREATE,
        Permission.CONVERSATION_READ,
        Permission.RUN_EXECUTE,
        Permission.TOOL_USE,
    },
}


@dataclass
class UserQuota:
    requests_per_minute: int = 60
    max_tokens_per_day: int = 100_000
    max_storage_bytes: int = 50 * 1024 * 1024  # 50 MB
    used_tokens_today: int = 0
    used_storage_bytes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "requests_per_minute": self.requests_per_minute,
            "max_tokens_per_day": self.max_tokens_per_day,
            "max_storage_bytes": self.max_storage_bytes,
            "used_tokens_today": self.used_tokens_today,
            "used_storage_bytes": self.used_storage_bytes,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserQuota:
        return cls(
            requests_per_minute=data.get("requests_per_minute", 60),
            max_tokens_per_day=data.get("max_tokens_per_day", 100_000),
            max_storage_bytes=data.get("max_storage_bytes", 50 * 1024 * 1024),
            used_tokens_today=data.get("used_tokens_today", 0),
            used_storage_bytes=data.get("used_storage_bytes", 0),
        )


@dataclass
class User:
    id: str
    username: str
    password_hash: str
    salt: str
    role: UserRole = UserRole.MEMBER
    email: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    is_active: bool = True
    quotas: UserQuota = field(default_factory=UserQuota)

    def has_permission(self, permission: Permission) -> bool:
        allowed = ROLE_PERMISSIONS.get(self.role, set())
        return permission in allowed

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "role": self.role.value,
            "email": self.email,
            "created_at": self.created_at,
            "is_active": self.is_active,
            "quotas": self.quotas.to_dict(),
        }


@dataclass
class Session:
    token: str
    user_id: str
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str = ""
    is_revoked: bool = False

    def is_valid(self) -> bool:
        if self.is_revoked:
            return False
        if not self.expires_at:
            return True
        now = datetime.now(UTC).isoformat()
        return now < self.expires_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "token": self.token,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "is_revoked": self.is_revoked,
        }
