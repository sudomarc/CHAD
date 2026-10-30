from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum


class OperationType(str, Enum):
    READ = "read"
    WRITE = "write"


@dataclass(frozen=True, slots=True)
class OAuthToken:
    access_token: str
    refresh_token: str | None = None
    token_type: str = "Bearer"
    expires_at: float | None = None
    scopes: set[str] = field(default_factory=set)

    def is_expired(self, current_time: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        now = current_time if current_time is not None else time.time()
        return now >= self.expires_at

    def has_scope(self, required_scope: str) -> bool:
        return required_scope in self.scopes or "*" in self.scopes


@dataclass(frozen=True, slots=True)
class ConnectorHealth:
    service: str
    status: str  # "healthy", "unhealthy", "revoked", "unauthenticated"
    message: str = ""
    latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class SideEffectConfirmation:
    operation: str
    details: dict = field(default_factory=dict)
    confirmed: bool = False


class ConnectorError(Exception):
    """Base exception for external connectors."""


class AuthError(ConnectorError):
    """Raised when authentication fails or token is missing/expired."""


class ScopeError(ConnectorError):
    """Raised when the OAuth token lacks required scope for an operation."""


class SideEffectDeniedError(ConnectorError):
    """Raised when a write/side-effect operation lacks explicit confirmation."""


class ConnectorRevokedError(ConnectorError):
    """Raised when attempting to use a revoked connector."""
