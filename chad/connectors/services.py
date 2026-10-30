from __future__ import annotations

from chad.connectors.base import BaseConnector
from chad.connectors.models import ConnectorError, OperationType


class GitHubConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__("github")

    def execute(
        self,
        operation: str,
        op_type: OperationType = OperationType.READ,
        params: dict | None = None,
        confirmed: bool = False,
    ) -> dict:
        params = params or {}
        required_scope = "repo:write" if op_type == OperationType.WRITE else "repo:read"
        self.validate_access(required_scope)
        self.enforce_side_effect_policy(operation, op_type, confirmed)

        if op_type == OperationType.READ and operation in ("list_repos", "get_issue"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed read {operation} with params {params}"},
            }
        if op_type == OperationType.WRITE and operation in ("create_issue", "merge_pr"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed write {operation} with params {params}"},
            }
        raise ConnectorError(f"Unsupported operation '{operation}' for service '{self.service_name}'.")


class NotionConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__("notion")

    def execute(
        self,
        operation: str,
        op_type: OperationType = OperationType.READ,
        params: dict | None = None,
        confirmed: bool = False,
    ) -> dict:
        params = params or {}
        required_scope = "page:write" if op_type == OperationType.WRITE else "page:read"
        self.validate_access(required_scope)
        self.enforce_side_effect_policy(operation, op_type, confirmed)

        if op_type == OperationType.READ and operation in ("get_page", "search_pages"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed read {operation} with params {params}"},
            }
        if op_type == OperationType.WRITE and operation in ("create_page", "update_page"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed write {operation} with params {params}"},
            }
        raise ConnectorError(f"Unsupported operation '{operation}' for service '{self.service_name}'.")


class DriveConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__("drive")

    def execute(
        self,
        operation: str,
        op_type: OperationType = OperationType.READ,
        params: dict | None = None,
        confirmed: bool = False,
    ) -> dict:
        params = params or {}
        required_scope = "drive:write" if op_type == OperationType.WRITE else "drive:read"
        self.validate_access(required_scope)
        self.enforce_side_effect_policy(operation, op_type, confirmed)

        if op_type == OperationType.READ and operation in ("list_files", "get_file"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed read {operation} with params {params}"},
            }
        if op_type == OperationType.WRITE and operation in ("upload_file", "delete_file"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed write {operation} with params {params}"},
            }
        raise ConnectorError(f"Unsupported operation '{operation}' for service '{self.service_name}'.")


class SlackConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__("slack")

    def execute(
        self,
        operation: str,
        op_type: OperationType = OperationType.READ,
        params: dict | None = None,
        confirmed: bool = False,
    ) -> dict:
        params = params or {}
        required_scope = "slack:write" if op_type == OperationType.WRITE else "slack:read"
        self.validate_access(required_scope)
        self.enforce_side_effect_policy(operation, op_type, confirmed)

        if op_type == OperationType.READ and operation in ("list_channels", "read_messages"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed read {operation} with params {params}"},
            }
        if op_type == OperationType.WRITE and operation in ("post_message", "delete_message"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed write {operation} with params {params}"},
            }
        raise ConnectorError(f"Unsupported operation '{operation}' for service '{self.service_name}'.")


class CalendarConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__("calendar")

    def execute(
        self,
        operation: str,
        op_type: OperationType = OperationType.READ,
        params: dict | None = None,
        confirmed: bool = False,
    ) -> dict:
        params = params or {}
        required_scope = "calendar:write" if op_type == OperationType.WRITE else "calendar:read"
        self.validate_access(required_scope)
        self.enforce_side_effect_policy(operation, op_type, confirmed)

        if op_type == OperationType.READ and operation in ("list_events", "get_event"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed read {operation} with params {params}"},
            }
        if op_type == OperationType.WRITE and operation in ("create_event", "delete_event"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed write {operation} with params {params}"},
            }
        raise ConnectorError(f"Unsupported operation '{operation}' for service '{self.service_name}'.")


class EmailConnector(BaseConnector):
    def __init__(self) -> None:
        super().__init__("email")

    def execute(
        self,
        operation: str,
        op_type: OperationType = OperationType.READ,
        params: dict | None = None,
        confirmed: bool = False,
    ) -> dict:
        params = params or {}
        required_scope = "email:write" if op_type == OperationType.WRITE else "email:read"
        self.validate_access(required_scope)
        self.enforce_side_effect_policy(operation, op_type, confirmed)

        if op_type == OperationType.READ and operation in ("list_emails", "get_email"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed read {operation} with params {params}"},
            }
        if op_type == OperationType.WRITE and operation in ("send_email", "delete_email"):
            return {
                "service": self.service_name,
                "operation": operation,
                "status": "success",
                "data": {"result": f"Executed write {operation} with params {params}"},
            }
        raise ConnectorError(f"Unsupported operation '{operation}' for service '{self.service_name}'.")
