from __future__ import annotations

from typing import Any

from chad.connectors.base import BaseConnector
from chad.connectors.models import (
    ConnectorHealth,
    ConnectorOperation,
    ConnectorType,
    OAuthToken,
)


class ConnectorRegistry:
    """Registry for managing and executing external connectors."""

    def __init__(self) -> None:
        self._connectors: dict[ConnectorType, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        """Registers a connector instance."""
        self._connectors[connector.connector_type] = connector

    def get(self, connector_type: ConnectorType | str) -> BaseConnector:
        """Retrieves a registered connector."""
        try:
            ctype = ConnectorType(connector_type) if isinstance(connector_type, str) else connector_type
        except ValueError as exc:
            raise KeyError(f"Connector '{connector_type}' is not registered.") from exc

        if ctype not in self._connectors:
            raise KeyError(f"Connector '{ctype.value}' is not registered.")
        return self._connectors[ctype]

    def is_registered(self, connector_type: ConnectorType | str) -> bool:
        """Checks if a connector is registered."""
        try:
            ctype = ConnectorType(connector_type) if isinstance(connector_type, str) else connector_type
            return ctype in self._connectors
        except ValueError:
            return False

    def list_connectors(self) -> list[BaseConnector]:
        """Lists all registered connectors."""
        return list(self._connectors.values())

    def authenticate(self, connector_type: ConnectorType | str, token: OAuthToken) -> None:
        """Authenticates a registered connector with an OAuth token."""
        connector = self.get(connector_type)
        connector.authenticate(token)

    def revoke(self, connector_type: ConnectorType | str) -> None:
        """Revokes credentials for a registered connector."""
        connector = self.get(connector_type)
        connector.revoke()

    def health_check_all(self) -> dict[str, ConnectorHealth]:
        """Performs health check across all registered connectors."""
        results: dict[str, ConnectorHealth] = {}
        for ctype, connector in self._connectors.items():
            results[ctype.value] = connector.health_check()
        return results

    def execute_operation(
        self,
        operation: ConnectorOperation,
        confirmed: bool = False,
    ) -> dict[str, Any]:
        """Dispatches an operation to the appropriate connector."""
        connector = self.get(operation.connector_type)
        return connector.execute_operation(operation, confirmed=confirmed)
