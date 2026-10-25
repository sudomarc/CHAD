from __future__ import annotations

from typing import Any
from chad.connectors.base import (
    BaseConnector,
    ConnectorAccessLevel,
    ConnectorError,
    ConnectorStatus,
)
from chad.tools.schema import ToolDefinition, ToolPermissionLevel


class ConnectorRegistry:
    """Registry managing external connectors, lifecycle, health, and tool generation."""

    def __init__(self) -> None:
        self._connectors: dict[str, BaseConnector] = {}

    def register(self, connector: BaseConnector) -> None:
        """Register a connector instance."""
        self._connectors[connector.connector_id] = connector

    def unregister(self, connector_id: str) -> bool:
        """Unregister a connector instance."""
        if connector_id in self._connectors:
            del self._connectors[connector_id]
            return True
        return False

    def get(self, connector_id: str) -> BaseConnector | None:
        """Get connector by ID."""
        return self._connectors.get(connector_id)

    def get_by_type(self, connector_type: str) -> list[BaseConnector]:
        """Get all registered connectors of a given type."""
        return [c for c in self._connectors.values() if c.connector_type == connector_type]

    def list_connectors(self) -> list[BaseConnector]:
        """List all registered connectors."""
        return list(self._connectors.values())

    def revoke(self, connector_id: str) -> None:
        """Revoke credentials and disconnect a specific connector."""
        connector = self.get(connector_id)
        if connector:
            connector.revoke()

    def health_check_all(self) -> dict[str, bool]:
        """Perform health checks on all registered connectors."""
        return {
            cid: connector.health_check()
            for cid, connector in self._connectors.items()
        }

    def execute_operation(
        self,
        connector_id: str,
        operation_name: str,
        params: dict[str, Any] | None = None,
        confirm_side_effects: bool = False,
    ) -> dict[str, Any]:
        """Execute operation on named connector."""
        connector = self.get(connector_id)
        if connector is None:
            raise ConnectorError(f"Connector '{connector_id}' not found in registry.")
        return connector.execute_operation(operation_name, params, confirm_side_effects)

    def generate_tools(self) -> list[ToolDefinition]:
        """Generate ToolDefinitions for all operations across connected connectors."""
        tools: list[ToolDefinition] = []
        for connector in self._connectors.values():
            if connector.status != ConnectorStatus.CONNECTED:
                continue
            for op_name, op_meta in connector.get_operations().items():
                perm = (
                    ToolPermissionLevel.USER_APPROVAL
                    if (op_meta.access_level == ConnectorAccessLevel.WRITE or op_meta.has_side_effect)
                    else ToolPermissionLevel.ALWAYS_ALLOW
                )
                tool_id = f"connector_{connector.connector_id}_{op_name}"
                tools.append(
                    ToolDefinition(
                        id=tool_id,
                        name=f"{connector.name}: {op_name}",
                        description=op_meta.description,
                        input_schema={
                            "type": "object",
                            "properties": {
                                "params": {"type": "object", "description": "Operation arguments"},
                                "confirm_side_effects": {
                                    "type": "boolean",
                                    "description": "Explicit confirmation for write/side-effect operations",
                                },
                            },
                        },
                        permission_level=perm,
                        side_effect_level="MUTATING" if op_meta.has_side_effect else "READ_ONLY",
                    )
                )
        return tools
