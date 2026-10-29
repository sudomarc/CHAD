from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from chad.connectors.models import (
    ConnectorHealth,
    ConnectorOperation,
    ConnectorOperationType,
    ConnectorStatus,
    ConnectorType,
    OAuthToken,
)


class ConnectorError(Exception):
    """Base exception for connector operations."""


class AuthenticationError(ConnectorError):
    """Exception raised when authentication fails or is missing."""


class InsufficientScopeError(ConnectorError):
    """Exception raised when required OAuth scope is missing."""


class SideEffectConfirmationRequiredError(ConnectorError):
    """Exception raised when write operation requires explicit side-effect confirmation."""


class BaseConnector(ABC):
    """Abstract base class for all external service connectors."""

    def __init__(self, connector_type: ConnectorType) -> None:
        self.connector_type = connector_type
        self._token: OAuthToken | None = None

    @property
    def token(self) -> OAuthToken | None:
        return self._token

    def authenticate(self, token: OAuthToken) -> None:
        """Sets or updates the OAuth token for the connector."""
        self._token = token

    def revoke(self) -> None:
        """Revokes credentials and disconnects the connector."""
        self._token = None

    def is_authenticated(self) -> bool:
        if self._token is None:
            return False
        return not self._token.is_expired()

    def validate_scopes(self, required_scope: str) -> None:
        if not self.is_authenticated():
            raise AuthenticationError(f"Connector {self.connector_type.value} is not authenticated.")
        assert self._token is not None
        if not self._token.has_scope(required_scope):
            raise InsufficientScopeError(
                f"Connector {self.connector_type.value} lacks required scope: {required_scope}"
            )

    def health_check(self) -> ConnectorHealth:
        if self._token is None:
            return ConnectorHealth(
                healthy=False,
                status=ConnectorStatus.DISCONNECTED,
                message="No OAuth token available.",
            )
        if self._token.is_expired():
            return ConnectorHealth(
                healthy=False,
                status=ConnectorStatus.EXPIRED,
                message="OAuth token is expired.",
            )
        return ConnectorHealth(
            healthy=True,
            status=ConnectorStatus.AUTHENTICATED,
            message="OK",
        )

    def execute_operation(
        self,
        operation: ConnectorOperation,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Executes a connector operation with scope validation and side-effect check."""
        if operation.connector_type != self.connector_type:
            raise ValueError(
                f"Operation type {operation.connector_type.value} does not match connector {self.connector_type.value}"
            )

        self.validate_scopes(operation.required_scope)

        if (
            operation.operation_type == ConnectorOperationType.WRITE
            and operation.requires_side_effect_confirmation
            and not confirmed
        ):
            raise SideEffectConfirmationRequiredError(
                f"Operation {operation.operation_id} requires explicit side-effect confirmation before execution."
            )

        return self._do_execute(operation)

    @abstractmethod
    def _do_execute(self, operation: ConnectorOperation) -> dict[str, Any]:
        """Internal operation execution to be implemented by specific provider connectors."""
        raise NotImplementedError
