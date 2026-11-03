from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from chad.auth.models import (
    ROLE_PERMISSIONS,
    AccessDeniedError,
    InvalidCredentialsError,
    Permission,
    User,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserRole,
    UserTier,
)


def hash_password(password: str, salt: bytes | None = None) -> str:
    if salt is None:
        salt = os.urandom(16)
    kdf = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}:{kdf.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, key_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(key_hex)
        computed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(expected, computed)
    except (ValueError, TypeError):
        return False


def generate_api_key(prefix: str = "chad_live_") -> str:
    random_part = secrets.token_urlsafe(32)
    return f"{prefix}{random_part}"


def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


@dataclass(slots=True)
class ApiKeyRecord:
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str = ""
    label: str = "Default API Key"
    key_prefix: str = ""
    key_hash: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    is_revoked: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "label": self.label,
            "key_prefix": self.key_prefix,
            "created_at": self.created_at,
            "is_revoked": self.is_revoked,
        }


class AuthEngine:
    """Manages user registration, authentication, RBAC, and API keys."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}  # user_id -> User
        self._username_index: dict[str, str] = {}  # lower(username) -> user_id
        self._email_index: dict[str, str] = {}  # lower(email) -> user_id
        self._api_keys: dict[str, ApiKeyRecord] = {}  # key_id -> ApiKeyRecord
        self._key_hash_index: dict[str, str] = {}  # key_hash -> key_id

    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        role: UserRole = UserRole.MEMBER,
        tier: UserTier = UserTier.FREE,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        u_norm = username.strip().lower()
        e_norm = email.strip().lower()
        if not u_norm:
            raise ValueError("Username cannot be empty")
        if not e_norm:
            raise ValueError("Email cannot be empty")
        if u_norm in self._username_index:
            raise UserAlreadyExistsError(f"Username '{username}' already exists")
        if e_norm in self._email_index:
            raise UserAlreadyExistsError(f"Email '{email}' already registered")

        user = User(
            username=username.strip(),
            email=email.strip(),
            password_hash=hash_password(password),
            role=role,
            tier=tier,
            metadata=metadata or {},
        )
        self._users[user.id] = user
        self._username_index[u_norm] = user.id
        self._email_index[e_norm] = user.id
        return user

    def authenticate_password(self, identifier: str, password: str) -> User:
        norm = identifier.strip().lower()
        user_id = self._username_index.get(norm) or self._email_index.get(norm)
        if user_id is None:
            raise InvalidCredentialsError("Invalid credentials")

        user = self._users[user_id]
        if not user.is_active:
            raise AccessDeniedError("User account is inactive")
        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Invalid credentials")
        return user

    def create_api_key(
        self,
        user_id: str,
        label: str = "Default API Key",
    ) -> tuple[ApiKeyRecord, str]:
        user = self.get_user(user_id)
        if not user.is_active:
            raise AccessDeniedError("Cannot create API key for inactive user")

        raw_key = generate_api_key()
        prefix = raw_key[:12]
        key_hash = hash_api_key(raw_key)

        record = ApiKeyRecord(
            user_id=user.id,
            label=label,
            key_prefix=prefix,
            key_hash=key_hash,
        )
        self._api_keys[record.id] = record
        self._key_hash_index[key_hash] = record.id
        return record, raw_key

    def authenticate_api_key(self, raw_key: str) -> tuple[User, ApiKeyRecord]:
        key_hash = hash_api_key(raw_key)
        key_id = self._key_hash_index.get(key_hash)
        if key_id is None:
            raise InvalidCredentialsError("Invalid API key")

        record = self._api_keys[key_id]
        if record.is_revoked:
            raise AccessDeniedError("API key has been revoked")

        user = self.get_user(record.user_id)
        if not user.is_active:
            raise AccessDeniedError("User account is inactive")

        return user, record

    def revoke_api_key(self, key_id: str) -> None:
        if key_id in self._api_keys:
            self._api_keys[key_id].is_revoked = True

    def get_user(self, user_id: str) -> User:
        user = self._users.get(user_id)
        if user is None:
            raise UserNotFoundError(f"User {user_id} not found")
        return user

    def list_users(self) -> list[User]:
        return list(self._users.values())

    def update_user(
        self,
        user_id: str,
        role: UserRole | None = None,
        tier: UserTier | None = None,
        is_active: bool | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> User:
        user = self.get_user(user_id)
        if role is not None:
            user.role = role
        if tier is not None:
            user.tier = tier
        if is_active is not None:
            user.is_active = is_active
        if metadata is not None:
            user.metadata.update(metadata)
        return user

    def has_permission(self, user: User, permission: Permission) -> bool:
        if not user.is_active:
            return False
        perms = ROLE_PERMISSIONS.get(user.role, set())
        return permission in perms

    def assert_permission(self, user: User, permission: Permission) -> None:
        if not self.has_permission(user, permission):
            raise AccessDeniedError(
                f"User '{user.username}' (role: {user.role.value}) lacks permission '{permission.value}'"
            )
