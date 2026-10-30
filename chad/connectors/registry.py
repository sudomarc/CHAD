from __future__ import annotations

from chad.connectors.base import BaseConnector
from chad.connectors.models import ConnectorError, ConnectorHealth


class ConnectorRegistry:
    """Registry for managing external service connectors."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        if not isinstance(connector, BaseConnector):
            raise ConnectorError("Invalid connector type provided.")
        self._connectors[connector.service_name] = connector

    def unregister(self, service_name: str) -> None:
        if service_name in self._connectors:
            del self._connectors[service_name]

    def get(self, service_name: str) -> BaseConnector:
        if service_name not in self._connectors:
            raise ConnectorError(f"Connector for service '{service_name}' is not registered.")
        return self._connectors[service_name]

    def list_connectors(self) -> list[str]:
        return list(self._connectors.keys())

    def health_check_all(self) -> dict[str, ConnectorHealth]:
        return {
            service_name: connector.health_check()
            for service_name, connector in self._connectors.items()
        }

    def revoke_all(self) -> None:
        for connector in self._connectors.values():
            connector.revoke()
