from __future__ import annotations

from typing import Any

from chad.connectors.base import BaseConnector
from chad.connectors.models import (
    ConnectorOperation,
    ConnectorType,
)


class GitHubConnector(BaseConnector):
    """GitHub external connector implementation."""

    def __init__(self) -> None:
        super().__init__(ConnectorType.GITHUB)

    def _do_execute(self, operation: ConnectorOperation) -> dict[str, Any]:
        return {
            "status": "success",
            "connector": self.connector_type.value,
            "operation_id": operation.operation_id,
            "type": operation.operation_type.value,
            "result": operation.payload,
        }


class NotionConnector(BaseConnector):
    """Notion external connector implementation."""

    def __init__(self) -> None:
        super().__init__(ConnectorType.NOTION)

    def _do_execute(self, operation: ConnectorOperation) -> dict[str, Any]:
        return {
            "status": "success",
            "connector": self.connector_type.value,
            "operation_id": operation.operation_id,
            "type": operation.operation_type.value,
            "result": operation.payload,
        }


class DriveConnector(BaseConnector):
    """Google Drive external connector implementation."""

    def __init__(self) -> None:
        super().__init__(ConnectorType.DRIVE)

    def _do_execute(self, operation: ConnectorOperation) -> dict[str, Any]:
        return {
            "status": "success",
            "connector": self.connector_type.value,
            "operation_id": operation.operation_id,
            "type": operation.operation_type.value,
            "result": operation.payload,
        }


class SlackConnector(BaseConnector):
    """Slack external connector implementation."""

    def __init__(self) -> None:
        super().__init__(ConnectorType.SLACK)

    def _do_execute(self, operation: ConnectorOperation) -> dict[str, Any]:
        return {
            "status": "success",
            "connector": self.connector_type.value,
            "operation_id": operation.operation_id,
            "type": operation.operation_type.value,
            "result": operation.payload,
        }


class CalendarConnector(BaseConnector):
    """Google Calendar external connector implementation."""

    def __init__(self) -> None:
        super().__init__(ConnectorType.CALENDAR)

    def _do_execute(self, operation: ConnectorOperation) -> dict[str, Any]:
        return {
            "status": "success",
            "connector": self.connector_type.value,
            "operation_id": operation.operation_id,
            "type": operation.operation_type.value,
            "result": operation.payload,
        }


class EmailConnector(BaseConnector):
    """Email external connector implementation."""

    def __init__(self) -> None:
        super().__init__(ConnectorType.EMAIL)

    def _do_execute(self, operation: ConnectorOperation) -> dict[str, Any]:
        return {
            "status": "success",
            "connector": self.connector_type.value,
            "operation_id": operation.operation_id,
            "type": operation.operation_type.value,
            "result": operation.payload,
        }
