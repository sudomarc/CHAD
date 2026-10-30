from __future__ import annotations

import time
from abc import ABC, abstractmethod

from chad.connectors.models import (
    AuthError,
    ConnectorError,
    ConnectorHealth,
    ConnectorRevokedError,
    OAuthToken,
    OperationType,
    ScopeError,
    SideEffectDeniedError,
)


class BaseConnector(ABC):
    """Abstract base class for all external service connectors."""

    def __init__(self, service_name: str) -> None:
        self._service_name = service_name
        self._token: OAuthToken | None = None
        self._is_revoked: bool = False

    @property
    def service_name(self) -> str:
        return self._service_name

    @property
    def token(self) -> OAuthToken | None:
        return self._token

    @property
    def is_revoked(self) -> bool:
        return self._is_revoked

    def authenticate(self, token: OAuthToken) -> None:
        if not isinstance(token, OAuthToken) or not token.access_token:
            raise AuthError("Invalid OAuthToken provided.")
        self._token = token
        self._is_revoked = False

    def revoke(self) -> None:
        self._token = None
        self._is_revoked = True

    def health_check(self) -> ConnectorHealth:
        start = time.perf_counter()
        if self._is_revoked:
            latency = (time.perf_counter() - start) * 1000
            return ConnectorHealth(
                service=self._service_name,
                status="revoked",
                message="Connector has been revoked.",
                latency_ms=latency,
            )
        if self._token is None:
            latency = (time.perf_counter() - start) * 1000
            return ConnectorHealth(
                service=self._service_name,
                status="unauthenticated",
                message="No OAuth token present.",
                latency_ms=latency,
            )
        if self._token.is_expired():
            latency = (time.perf_counter() - start) * 1000
            return ConnectorHealth(
                service=self._service_name,
                status="unhealthy",
                message="OAuth token has expired.",
                latency_ms=latency,
            )
        latency = (time.perf_counter() - start) * 1000
        return ConnectorHealth(
            service=self._service_name,
            status="healthy",
            message="Connector is operational.",
            latency_ms=latency,
        )

    def validate_access(self, required_scope: str) -> None:
        if self._is_revoked:
            raise ConnectorRevokedError(f"Connector for service '{self._service_name}' is revoked.")
        if self._token is None:
            raise AuthError(f"Connector for service '{self._service_name}' is not authenticated.")
        if self._token.is_expired():
            raise AuthError(f"OAuth token for service '{self._service_name}' is expired.")
        if not self._token.has_scope(required_scope):
            raise ScopeError(
                f"Required scope '{required_scope}' missing for service '{self._service_name}'."
            )

    def enforce_side_effect_policy(
        self, operation: str, op_type: OperationType, confirmed: bool
    ) -> None:
        if op_type == OperationType.WRITE and not confirmed:
            raise SideEffectDeniedError(
                f"Write operation '{operation}' on service '{self._service_name}' requires explicit side-effect confirmation."
            )

    @abstractmethod
    def execute(
        self,
        operation: str,
        op_type: OperationType = OperationType.READ,
        params: dict | None = None,
        confirmed: bool = False,
    ) -> dict:
        """Executes an operation against the external service."""
