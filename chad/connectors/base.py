from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Any

from chad.connectors.models import (
    ConnectorActionInfo,
    ConnectorHealth,
    ConnectorResult,
    ConnectorType,
    OAuthToken,
)


class ConnectorError(Exception):
    pass


class TokenExpiredError(ConnectorError):
    pass


class ScopeError(ConnectorError):
    pass


class SideEffectConfirmationRequiredError(ConnectorError):
    pass


class BaseConnector(ABC):
    """Base class for all external service connectors."""

    def __init__(
        self,
        connector_id: str,
        connector_type: ConnectorType,
        token: OAuthToken | None = None,
    ) -> None:
        self.connector_id = connector_id
        self.connector_type = connector_type
        self._token: OAuthToken | None = token
        self._revoked: bool = False

    @property
    def is_connected(self) -> bool:
        return self._token is not None and not self._revoked

    def set_token(self, token: OAuthToken) -> None:
        self._token = token
        self._revoked = False

    def revoke_token(self) -> bool:
        """Revoke active credentials."""
        self._token = None
        self._revoked = True
        return True

    def check_health(self) -> ConnectorHealth:
        """Perform a health check on the connection."""
        start = time.perf_counter()
        now = time.time()
        if not self.is_connected:
            return ConnectorHealth(
                connected=False,
                status_message="Disconnected: No active token or token revoked.",
                latency_ms=0.0,
                last_checked_at=now,
            )
        assert self._token is not None
        if self._token.is_expired(now):
            return ConnectorHealth(
                connected=False,
                status_message="Disconnected: OAuth token has expired.",
                latency_ms=(time.perf_counter() - start) * 1000.0,
                last_checked_at=now,
            )

        latency = (time.perf_counter() - start) * 1000.0
        return ConnectorHealth(
            connected=True,
            status_message="Healthy",
            latency_ms=latency,
            last_checked_at=now,
        )

    def validate_action(
        self,
        action_name: str,
        side_effect_confirmed: bool = False,
    ) -> ConnectorActionInfo:
        """Validate token status, scopes, and side-effect requirements before executing an action."""
        if not self.is_connected:
            raise ConnectorError(f"Connector '{self.connector_id}' is not connected.")
        assert self._token is not None
        if self._token.is_expired():
            raise TokenExpiredError(f"Token for connector '{self.connector_id}' is expired.")

        actions = self.list_actions()
        action_info = actions.get(action_name)
        if action_info is None:
            raise ConnectorError(f"Unknown action '{action_name}' for connector '{self.connector_id}'.")

        # Scope validation
        for required_scope in action_info.required_scopes:
            if required_scope not in self._token.scopes:
                raise ScopeError(
                    f"Missing required scope '{required_scope}' for action '{action_name}' "
                    f"on connector '{self.connector_id}'."
                )

        # Read / Write separation & Side-effect confirmation
        if action_info.is_write and not side_effect_confirmed:
            raise SideEffectConfirmationRequiredError(
                f"Action '{action_name}' on connector '{self.connector_id}' produces side effects "
                "and requires explicit side_effect_confirmed=True."
            )

        return action_info

    @abstractmethod
    def list_actions(self) -> dict[str, ConnectorActionInfo]:
        """Return a mapping of supported action names to ConnectorActionInfo."""
        ...

    @abstractmethod
    def execute_action(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
        side_effect_confirmed: bool = False,
    ) -> ConnectorResult:
        """Execute a connector action."""
        ...
