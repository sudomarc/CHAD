from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class ConnectorType(str, Enum):
    GITHUB = "github"
    NOTION = "notion"
    GOOGLE_DRIVE = "google_drive"
    SLACK = "slack"
    CALENDAR = "calendar"
    EMAIL = "email"


@dataclass(frozen=True, slots=True)
class OAuthToken:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    scopes: tuple[str, ...] = field(default_factory=tuple)
    token_type: str = "Bearer"

    def is_expired(self, current_time: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        now = current_time if current_time is not None else time.time()
        return now >= self.expires_at


@dataclass(frozen=True, slots=True)
class ConnectorHealth:
    connected: bool
    status_message: str
    latency_ms: float | None = None
    last_checked_at: float | None = None


@dataclass(frozen=True, slots=True)
class ConnectorActionInfo:
    name: str
    is_write: bool = False
    required_scopes: tuple[str, ...] = field(default_factory=tuple)
    description: str = ""


@dataclass(frozen=True, slots=True)
class ConnectorResult:
    success: bool
    action: str
    data: dict | list | None = None
    error: str | None = None
    side_effect_confirmed: bool = False
