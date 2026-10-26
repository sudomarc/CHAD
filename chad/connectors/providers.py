from __future__ import annotations

from typing import Any

from chad.connectors.base import BaseConnector
from chad.connectors.models import (
    ConnectorActionInfo,
    ConnectorResult,
    ConnectorType,
    OAuthToken,
)


class GitHubConnector(BaseConnector):
    def __init__(self, connector_id: str = "github_default", token: OAuthToken | None = None) -> None:
        super().__init__(connector_id=connector_id, connector_type=ConnectorType.GITHUB, token=token)

    def list_actions(self) -> dict[str, ConnectorActionInfo]:
        return {
            "list_repos": ConnectorActionInfo(
                name="list_repos",
                is_write=False,
                required_scopes=("repo:read",),
                description="List repositories accessible to the user.",
            ),
            "create_issue": ConnectorActionInfo(
                name="create_issue",
                is_write=True,
                required_scopes=("repo:write",),
                description="Create an issue in a GitHub repository.",
            ),
        }

    def execute_action(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
        side_effect_confirmed: bool = False,
    ) -> ConnectorResult:
        self.validate_action(action_name, side_effect_confirmed=side_effect_confirmed)
        params = params or {}

        if action_name == "list_repos":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"repositories": ["sudomarc/CHAD", "sudomarc/LapisLLM"]},
            )
        elif action_name == "create_issue":
            repo = params.get("repo", "sudomarc/CHAD")
            title = params.get("title", "New issue")
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"issue_id": 101, "repo": repo, "title": title, "status": "open"},
                side_effect_confirmed=side_effect_confirmed,
            )
        return ConnectorResult(success=False, action=action_name, error=f"Unhandled action {action_name}")


class NotionConnector(BaseConnector):
    def __init__(self, connector_id: str = "notion_default", token: OAuthToken | None = None) -> None:
        super().__init__(connector_id=connector_id, connector_type=ConnectorType.NOTION, token=token)

    def list_actions(self) -> dict[str, ConnectorActionInfo]:
        return {
            "query_database": ConnectorActionInfo(
                name="query_database",
                is_write=False,
                required_scopes=("notion:read",),
                description="Query Notion database entries.",
            ),
            "append_block": ConnectorActionInfo(
                name="append_block",
                is_write=True,
                required_scopes=("notion:write",),
                description="Append content block to Notion page.",
            ),
        }

    def execute_action(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
        side_effect_confirmed: bool = False,
    ) -> ConnectorResult:
        self.validate_action(action_name, side_effect_confirmed=side_effect_confirmed)
        params = params or {}

        if action_name == "query_database":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"results": [{"id": "page_1", "title": "Project Roadmap"}]},
            )
        elif action_name == "append_block":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"block_id": "blk_999", "status": "appended"},
                side_effect_confirmed=side_effect_confirmed,
            )
        return ConnectorResult(success=False, action=action_name, error=f"Unhandled action {action_name}")


class GoogleDriveConnector(BaseConnector):
    def __init__(self, connector_id: str = "drive_default", token: OAuthToken | None = None) -> None:
        super().__init__(connector_id=connector_id, connector_type=ConnectorType.GOOGLE_DRIVE, token=token)

    def list_actions(self) -> dict[str, ConnectorActionInfo]:
        return {
            "search_files": ConnectorActionInfo(
                name="search_files",
                is_write=False,
                required_scopes=("drive.readonly",),
                description="Search files in Google Drive.",
            ),
            "upload_file": ConnectorActionInfo(
                name="upload_file",
                is_write=True,
                required_scopes=("drive.file",),
                description="Upload a new file to Google Drive.",
            ),
        }

    def execute_action(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
        side_effect_confirmed: bool = False,
    ) -> ConnectorResult:
        self.validate_action(action_name, side_effect_confirmed=side_effect_confirmed)
        params = params or {}

        if action_name == "search_files":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"files": [{"id": "file_123", "name": "Architecture Spec.pdf"}]},
            )
        elif action_name == "upload_file":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"file_id": "file_789", "name": params.get("filename", "untitled.txt")},
                side_effect_confirmed=side_effect_confirmed,
            )
        return ConnectorResult(success=False, action=action_name, error=f"Unhandled action {action_name}")


class SlackConnector(BaseConnector):
    def __init__(self, connector_id: str = "slack_default", token: OAuthToken | None = None) -> None:
        super().__init__(connector_id=connector_id, connector_type=ConnectorType.SLACK, token=token)

    def list_actions(self) -> dict[str, ConnectorActionInfo]:
        return {
            "read_messages": ConnectorActionInfo(
                name="read_messages",
                is_write=False,
                required_scopes=("channels:history",),
                description="Read messages from Slack channel.",
            ),
            "post_message": ConnectorActionInfo(
                name="post_message",
                is_write=True,
                required_scopes=("chat:write",),
                description="Post a message to a Slack channel.",
            ),
        }

    def execute_action(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
        side_effect_confirmed: bool = False,
    ) -> ConnectorResult:
        self.validate_action(action_name, side_effect_confirmed=side_effect_confirmed)
        params = params or {}

        if action_name == "read_messages":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"messages": [{"user": "U123", "text": "Hello team!"}]},
            )
        elif action_name == "post_message":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"ts": "1700000000.000100", "channel": params.get("channel", "general")},
                side_effect_confirmed=side_effect_confirmed,
            )
        return ConnectorResult(success=False, action=action_name, error=f"Unhandled action {action_name}")


class CalendarConnector(BaseConnector):
    def __init__(self, connector_id: str = "calendar_default", token: OAuthToken | None = None) -> None:
        super().__init__(connector_id=connector_id, connector_type=ConnectorType.CALENDAR, token=token)

    def list_actions(self) -> dict[str, ConnectorActionInfo]:
        return {
            "list_events": ConnectorActionInfo(
                name="list_events",
                is_write=False,
                required_scopes=("calendar.readonly",),
                description="List upcoming calendar events.",
            ),
            "create_event": ConnectorActionInfo(
                name="create_event",
                is_write=True,
                required_scopes=("calendar.events",),
                description="Create a calendar event.",
            ),
        }

    def execute_action(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
        side_effect_confirmed: bool = False,
    ) -> ConnectorResult:
        self.validate_action(action_name, side_effect_confirmed=side_effect_confirmed)
        params = params or {}

        if action_name == "list_events":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"events": [{"id": "event_1", "summary": "Sprint Sync"}]},
            )
        elif action_name == "create_event":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"event_id": "event_99", "summary": params.get("summary", "New Event")},
                side_effect_confirmed=side_effect_confirmed,
            )
        return ConnectorResult(success=False, action=action_name, error=f"Unhandled action {action_name}")


class EmailConnector(BaseConnector):
    def __init__(self, connector_id: str = "email_default", token: OAuthToken | None = None) -> None:
        super().__init__(connector_id=connector_id, connector_type=ConnectorType.EMAIL, token=token)

    def list_actions(self) -> dict[str, ConnectorActionInfo]:
        return {
            "fetch_emails": ConnectorActionInfo(
                name="fetch_emails",
                is_write=False,
                required_scopes=("mail.read",),
                description="Fetch emails from inbox.",
            ),
            "send_email": ConnectorActionInfo(
                name="send_email",
                is_write=True,
                required_scopes=("mail.send",),
                description="Send an email.",
            ),
        }

    def execute_action(
        self,
        action_name: str,
        params: dict[str, Any] | None = None,
        side_effect_confirmed: bool = False,
    ) -> ConnectorResult:
        self.validate_action(action_name, side_effect_confirmed=side_effect_confirmed)
        params = params or {}

        if action_name == "fetch_emails":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"emails": [{"id": "msg_001", "subject": "Welcome to CHAD"}]},
            )
        elif action_name == "send_email":
            return ConnectorResult(
                success=True,
                action=action_name,
                data={"message_id": "msg_999", "to": params.get("to", "user@example.com")},
                side_effect_confirmed=side_effect_confirmed,
            )
        return ConnectorResult(success=False, action=action_name, error=f"Unhandled action {action_name}")
