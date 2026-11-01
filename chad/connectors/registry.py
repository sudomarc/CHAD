from __future__ import annotations

from chad.connectors.base import BaseConnector, ConnectorError, ConnectorHealth


class ConnectorRegistry:
    """Registry for managing and inspecting external service connectors."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        self._connectors[connector.connector_type] = connector

    def unregister(self, connector_type: str) -> None:
        if connector_type in self._connectors:
            del self._connectors[connector_type]

    def get(self, connector_type: str) -> BaseConnector:
        connector = self._connectors.get(connector_type)
        if connector is None:
            raise ConnectorError(
                f"Connector '{connector_type}' is not registered in ConnectorRegistry."
            )
        return connector

    def list_connectors(self) -> list[BaseConnector]:
        return list(self._connectors.values())

    def check_all_health(self) -> dict[str, ConnectorHealth]:
        return {
            conn_type: connector.check_health()
            for conn_type, connector in self._connectors.items()
        }
