from __future__ import annotations

from chad.connectors.base import BaseConnector, ConnectorError
from chad.connectors.models import ConnectorHealth, ConnectorType


class ConnectorRegistry:
    """Central registry to manage external connector instances."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        self._connectors[connector.connector_id] = connector

    def unregister(self, connector_id: str) -> None:
        if connector_id in self._connectors:
            del self._connectors[connector_id]

    def get(self, connector_id: str) -> BaseConnector:
        if connector_id not in self._connectors:
            raise ConnectorError(f"Connector '{connector_id}' is not registered.")
        return self._connectors[connector_id]

    def list_connectors(self) -> list[str]:
        return list(self._connectors.keys())

    def list_by_type(self, connector_type: ConnectorType) -> list[BaseConnector]:
        return [
            conn for conn in self._connectors.values()
            if conn.connector_type == connector_type
        ]

    def check_all_health(self) -> dict[str, ConnectorHealth]:
        return {
            cid: conn.check_health()
            for cid, conn in self._connectors.items()
        }
