from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum


class ConnectorAccessLevel(str, Enum):
    READ = "read"
    WRITE = "write"


class ConnectorStatus(str, Enum):
    CONNECTED = "connected"
    EXPIRED = "expired"
    REVOKED = "revoked"
    DISCONNECTED = "disconnected"
    UNHEALTHY = "unhealthy"


@dataclass(frozen=True, slots=True)
class ConnectorScope:
    name: str
    description: str
    access_level: ConnectorAccessLevel = ConnectorAccessLevel.READ


@dataclass
class OAuthToken:
    access_token: str
    refresh_token: str | None = None
    expires_at: float | None = None  # unix timestamp
    scopes: tuple[str, ...] = ()
    token_type: str = "Bearer"

    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() >= self.expires_at


class ConnectorError(Exception):
    """Base exception for external connectors."""


class OAuthScopeError(ConnectorError):
    """Raised when an operation requires scopes not present on the OAuth token."""


class SideEffectConfirmationRequiredError(ConnectorError):
    """Raised when a write operation with side effects requires explicit confirmation."""

    def __init__(self, operation: str, connector_id: str, details: dict | None = None) -> None:
        self.operation = operation
        self.connector_id = connector_id
        self.details = details or {}
        super().__init__(
            f"Operation '{operation}' on connector '{connector_id}' has side effects "
            f"and requires explicit user confirmation."
        )


@dataclass(frozen=True, slots=True)
class OperationMetadata:
    name: str
    description: str
    access_level: ConnectorAccessLevel
    required_scopes: tuple[str, ...]
    has_side_effect: bool = False


class BaseConnector(ABC):
    """Abstract base class for external service connectors."""

    def __init__(
        self,
        connector_id: str,
        name: str,
        connector_type: str,
        supported_scopes: tuple[ConnectorScope, ...] = (),
    ) -> None:
        self.connector_id = connector_id
        self.name = name
        self.connector_type = connector_type
        self.supported_scopes = {s.name: s for s in supported_scopes}
        self.token: OAuthToken | None = None
        self._status: ConnectorStatus = ConnectorStatus.DISCONNECTED

    @property
    def status(self) -> ConnectorStatus:
        if self._status == ConnectorStatus.REVOKED:
            return ConnectorStatus.REVOKED
        if self.token is None:
            return ConnectorStatus.DISCONNECTED
        if self.token.is_expired():
            return ConnectorStatus.EXPIRED
        return self._status

    def connect(self, token: OAuthToken) -> None:
        """Connect or refresh credentials using an OAuth token."""
        self.token = token
        self._status = ConnectorStatus.CONNECTED

    def revoke(self) -> None:
        """Revoke current OAuth access token and disconnect."""
        self.token = None
        self._status = ConnectorStatus.REVOKED

    @abstractmethod
    def health_check(self) -> bool:
        """Perform a health check to verify connectivity and token validity."""

    @abstractmethod
    def get_operations(self) -> dict[str, OperationMetadata]:
        """Return a mapping of operation names to their metadata."""

    def check_operation_permissions(
        self,
        operation_name: str,
        confirm_side_effects: bool = False,
    ) -> OperationMetadata:
        """Validate status, OAuth scopes, and side-effect confirmation for an operation."""
        if self.status != ConnectorStatus.CONNECTED:
            raise ConnectorError(
                f"Connector '{self.connector_id}' is not connected (current status: {self.status.value})."
            )

        operations = self.get_operations()
        if operation_name not in operations:
            raise ConnectorError(f"Operation '{operation_name}' is not supported by connector '{self.connector_type}'.")

        op_meta = operations[operation_name]

        # Check scopes if token is present
        if self.token is not None:
            missing = [s for s in op_meta.required_scopes if s not in self.token.scopes]
            if missing:
                raise OAuthScopeError(
                    f"Operation '{operation_name}' requires scopes {op_meta.required_scopes}, missing: {missing}."
                )

        # Side-effect confirmation enforcement
        if (op_meta.access_level == ConnectorAccessLevel.WRITE or op_meta.has_side_effect) and not confirm_side_effects:
            raise SideEffectConfirmationRequiredError(
                operation=operation_name,
                connector_id=self.connector_id,
                details={"access_level": op_meta.access_level.value, "has_side_effect": op_meta.has_side_effect},
            )

        return op_meta

    @abstractmethod
    def execute_operation(
        self,
        operation_name: str,
        params: dict | None = None,
        confirm_side_effects: bool = False,
    ) -> dict:
        """Execute a named operation on the external service."""
