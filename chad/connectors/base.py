from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any


class ConnectorActionType(str, Enum):
    READ = "read"
    WRITE = "write"


class ConnectorError(Exception):
    """Base exception for external connectors."""


class UnauthenticatedError(ConnectorError):
    """Raised when an action is attempted on an unauthenticated connector."""


class TokenExpiredError(ConnectorError):
    """Raised when an action is attempted with an expired OAuth token."""


class InsufficientScopeError(ConnectorError):
    """Raised when an OAuth token lacks required scopes for an action."""


class SideEffectConfirmationRequiredError(ConnectorError):
    """Raised when a write/side-effect action requires explicit user confirmation."""


@dataclass(frozen=True, slots=True)
class OAuthToken:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None
    scopes: tuple[str, ...] = ()
    token_type: str = "Bearer"

    def is_expired(self, now: float | None = None) -> bool:
        if self.expires_at is None:
            return False
        current_time = now if now is not None else time.time()
        return current_time >= self.expires_at


class ScopeValidator:
    """Validates OAuth scopes."""

    @staticmethod
    def has_scope(
        granted_scopes: tuple[str, ...] | list[str], required_scope: str
    ) -> bool:
        granted_set = set(granted_scopes)
        if required_scope in granted_set:
            return True
        # Support wildcard matching, e.g. "repo" covers "repo:read"
        for granted in granted_set:
            if granted.endswith("*") and required_scope.startswith(granted[:-1]):
                return True
            if ":" in required_scope and granted == required_scope.split(":")[0]:
                return True
        return False

    @classmethod
    def validate_scopes(
        cls,
        granted_scopes: tuple[str, ...] | list[str],
        required_scopes: tuple[str, ...] | list[str],
    ) -> None:
        missing = [
            scope
            for scope in required_scopes
            if not cls.has_scope(granted_scopes, scope)
        ]
        if missing:
            raise InsufficientScopeError(
                f"OAuth token lacks required scopes: {', '.join(missing)}"
            )


@dataclass(frozen=True, slots=True)
class ConnectorHealth:
    status: str  # "healthy", "degraded", "unhealthy"
    message: str
    latency_ms: float | None = None


@dataclass(frozen=True, slots=True)
class ConnectorAction:
    name: str
    action_type: ConnectorActionType
    required_scopes: tuple[str, ...] = ()
    requires_side_effect_confirmation: bool = False


class BaseConnector(ABC):
    """Abstract base class for all external service connectors."""

    def __init__(self, token: OAuthToken | None = None) -> None:
        self._token: OAuthToken | None = token
        self._actions: dict[str, ConnectorAction] = {}
        self._register_actions()

    @property
    @abstractmethod
    def connector_type(self) -> str:
        """Type/identifier of the connector (e.g., 'github', 'slack')."""

    @property
    @abstractmethod
    def supported_scopes(self) -> tuple[str, ...]:
        """All supported scopes for this connector."""

    @abstractmethod
    def _register_actions(self) -> None:
        """Register supported actions for this connector."""

    @abstractmethod
    def _perform_action(
        self, action_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        """Internal implementation for executing actions."""

    @property
    def token(self) -> OAuthToken | None:
        return self._token

    @property
    def is_authenticated(self) -> bool:
        return self._token is not None and not self._token.is_expired()

    def set_token(self, token: OAuthToken) -> None:
        self._token = token

    def revoke_token(self) -> bool:
        """Revokes the current OAuth token."""
        if self._token is None:
            return False
        self._token = None
        return True

    def check_health(self) -> ConnectorHealth:
        """Checks health and connection status of the connector."""
        if self._token is None:
            return ConnectorHealth(
                status="unhealthy", message="Unauthenticated: No token configured."
            )
        if self._token.is_expired():
            return ConnectorHealth(
                status="unhealthy", message="Unauthenticated: Token expired."
            )
        start = time.perf_counter()
        # Simulated health ping check
        latency = (time.perf_counter() - start) * 1000
        return ConnectorHealth(
            status="healthy",
            message=f"{self.connector_type.capitalize()} connector is active and connected.",
            latency_ms=latency,
        )

    def execute(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Executes an action with scope validation, read/write separation, and side-effect confirmation."""
        if self._token is None:
            raise UnauthenticatedError(
                f"Connector {self.connector_type} is not authenticated."
            )
        if self._token.is_expired():
            raise TokenExpiredError(
                f"OAuth token for {self.connector_type} has expired."
            )

        action = self._actions.get(action_name)
        if action is None:
            raise ConnectorError(
                f"Action '{action_name}' is not supported by {self.connector_type} connector."
            )

        ScopeValidator.validate_scopes(self._token.scopes, action.required_scopes)

        if (
            action.action_type == ConnectorActionType.WRITE
            or action.requires_side_effect_confirmation
        ) and not confirmed:
            raise SideEffectConfirmationRequiredError(
                f"Action '{action_name}' on {self.connector_type} causes external side-effects and requires explicit user confirmation."
            )

        return self._perform_action(action_name, params or {})
