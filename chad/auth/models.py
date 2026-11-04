from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4


class UserRole(StrEnum):
    ADMIN = "admin"
    MEMBER = "member"
    GUEST = "guest"


class UserTier(StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"


class Permission(StrEnum):
    CONVERSATION_READ = "conversation:read"
    CONVERSATION_WRITE = "conversation:write"
    CONVERSATION_DELETE = "conversation:delete"
    TOOL_INVOKE = "tool:invoke"
    CODE_EXECUTE = "code:execute"
    USER_MANAGE = "user:manage"
    ADMIN_CONFIG = "admin:config"


ROLE_PERMISSIONS: dict[UserRole, set[Permission]] = {
    UserRole.ADMIN: {
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
        Permission.CONVERSATION_DELETE,
        Permission.TOOL_INVOKE,
        Permission.CODE_EXECUTE,
        Permission.USER_MANAGE,
        Permission.ADMIN_CONFIG,
    },
    UserRole.MEMBER: {
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
        Permission.CONVERSATION_DELETE,
        Permission.TOOL_INVOKE,
        Permission.CODE_EXECUTE,
    },
    UserRole.GUEST: {
        Permission.CONVERSATION_READ,
        Permission.CONVERSATION_WRITE,
    },
}


# Authentication & Authorization Exceptions
class AuthError(Exception):
    """Base exception for authentication and authorization errors."""


class InvalidCredentialsError(AuthError):
    """Raised when password or token verification fails."""


class UserNotFoundError(AuthError):
    """Raised when the specified user cannot be found."""


class UserAlreadyExistsError(AuthError):
    """Raised when attempting to create a user with an existing username/email."""


class SessionExpiredError(AuthError):
    """Raised when a session has expired or been revoked."""


class AccessDeniedError(AuthError):
    """Raised when an operation is forbidden due to role or tenant ownership."""


class QuotaExceededError(AuthError):
    """Base exception for quota violations."""


class RateLimitExceededError(QuotaExceededError):
    """Raised when request rate limit is exceeded."""


class TokenQuotaExceededError(QuotaExceededError):
    """Raised when token quota is exceeded."""


class StorageQuotaExceededError(QuotaExceededError):
    """Raised when user storage quota is exceeded."""


@dataclass(slots=True)
class User:
    id: str = field(default_factory=lambda: str(uuid4()))
    username: str = ""
    email: str = ""
    password_hash: str = ""
    role: UserRole = UserRole.MEMBER
    tier: UserTier = UserTier.FREE
    is_active: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "role": self.role.value,
            "tier": self.tier.value,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        return cls(
            id=str(data.get("id") or uuid4()),
            username=str(data.get("username", "")),
            email=str(data.get("email", "")),
            password_hash=str(data.get("password_hash", "")),
            role=UserRole(str(data.get("role", "member"))),
            tier=UserTier(str(data.get("tier", "free"))),
            is_active=bool(data.get("is_active", True)),
            created_at=str(data.get("created_at") or datetime.now(UTC).isoformat()),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass(slots=True)
class SessionRecord:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    token_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    expires_at: str = ""
    last_active_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    ip_address: str | None = None
    user_agent: str | None = None
    is_revoked: bool = False

    def is_valid(self, now: datetime | None = None) -> bool:
        if self.is_revoked:
            return False
        if not self.expires_at:
            return True
        current_time = now or datetime.now(UTC)
        try:
            exp = datetime.fromisoformat(self.expires_at)
            return current_time <= exp
        except ValueError:
            return False


@dataclass(frozen=True, slots=True)
class AuthContext:
    user: User
    session: SessionRecord | None = None
    api_key_id: str | None = None
    client_ip: str | None = None
    user_agent: str | None = None


@dataclass(frozen=True, slots=True)
class QuotaLimits:
    requests_per_minute: int = 30
    tokens_per_day: int = 100_000
    storage_bytes: int = 50 * 1024 * 1024  # 50 MB
    concurrent_tasks: int = 3


TIER_LIMITS: dict[UserTier, QuotaLimits] = {
    UserTier.FREE: QuotaLimits(
        requests_per_minute=20,
        tokens_per_day=50_000,
        storage_bytes=25 * 1024 * 1024,  # 25 MB
        concurrent_tasks=2,
    ),
    UserTier.PRO: QuotaLimits(
        requests_per_minute=120,
        tokens_per_day=500_000,
        storage_bytes=500 * 1024 * 1024,  # 500 MB
        concurrent_tasks=10,
    ),
    UserTier.ENTERPRISE: QuotaLimits(
        requests_per_minute=1000,
        tokens_per_day=10_000_000,
        storage_bytes=10 * 1024 * 1024 * 1024,  # 10 GB
        concurrent_tasks=50,
    ),
}


@dataclass(slots=True)
class QuotaUsage:
    user_id: str
    requests_count: int = 0
    tokens_used: int = 0
    storage_used_bytes: int = 0
    limits: QuotaLimits = field(default_factory=QuotaLimits)

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "requests_count": self.requests_count,
            "tokens_used": self.tokens_used,
            "storage_used_bytes": self.storage_used_bytes,
            "limits": {
                "requests_per_minute": self.limits.requests_per_minute,
                "tokens_per_day": self.limits.tokens_per_day,
                "storage_bytes": self.limits.storage_bytes,
                "concurrent_tasks": self.limits.concurrent_tasks,
            },
        }
