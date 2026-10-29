from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ConnectorType(str, Enum):
    GITHUB = "github"
    NOTION = "notion"
    DRIVE = "drive"
    SLACK = "slack"
    CALENDAR = "calendar"
    EMAIL = "email"


class ConnectorOperationType(str, Enum):
    READ = "read"
    WRITE = "write"


class ConnectorStatus(str, Enum):
    DISCONNECTED = "disconnected"
    AUTHENTICATED = "authenticated"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ConnectorScope:
    name: str
    description: str
    operation_type: ConnectorOperationType = ConnectorOperationType.READ


@dataclass(slots=True)
class OAuthToken:
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_at: float | None = None
    scopes: tuple[str, ...] = ()

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at

    def has_scope(self, required_scope: str) -> bool:
        return required_scope in self.scopes


@dataclass(frozen=True, slots=True)
class ConnectorHealth:
    healthy: bool
    status: ConnectorStatus
    message: str = "OK"
    last_checked: float = field(default_factory=time.time)


@dataclass(frozen=True, slots=True)
class ConnectorOperation:
    operation_id: str
    connector_type: ConnectorType
    operation_type: ConnectorOperationType
    required_scope: str
    payload: dict[str, Any] = field(default_factory=dict)
    requires_side_effect_confirmation: bool = False
