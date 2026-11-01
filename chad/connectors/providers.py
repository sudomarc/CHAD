from __future__ import annotations

from typing import Any

from chad.connectors.base import (
    BaseConnector,
    ConnectorAction,
    ConnectorActionType,
)


class GitHubConnector(BaseConnector):
    @property
    def connector_type(self) -> str:
        return "github"

    @property
    def supported_scopes(self) -> tuple[str, ...]:
        return ("repo:read", "repo:write", "issue:write", "pr:write")

    def _register_actions(self) -> None:
        self._actions = {
            "read_repo": ConnectorAction(
                name="read_repo",
                action_type=ConnectorActionType.READ,
                required_scopes=("repo:read",),
            ),
            "list_issues": ConnectorAction(
                name="list_issues",
                action_type=ConnectorActionType.READ,
                required_scopes=("repo:read",),
            ),
            "create_issue": ConnectorAction(
                name="create_issue",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("issue:write",),
                requires_side_effect_confirmation=True,
            ),
            "create_pull_request": ConnectorAction(
                name="create_pull_request",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("pr:write",),
                requires_side_effect_confirmation=True,
            ),
        }

    def _perform_action(
        self, action_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        if action_name == "read_repo":
            repo = params.get("repo", "sudomarc/CHAD")
            return {"status": "success", "repo": repo, "stars": 128, "forks": 16}
        if action_name == "list_issues":
            return {
                "status": "success",
                "issues": [{"id": 1, "title": "Initial issue"}],
            }
        if action_name == "create_issue":
            title = params.get("title", "New issue")
            return {"status": "success", "issue_id": 101, "title": title}
        if action_name == "create_pull_request":
            title = params.get("title", "New PR")
            return {"status": "success", "pr_id": 202, "title": title}
        return {}


class NotionConnector(BaseConnector):
    @property
    def connector_type(self) -> str:
        return "notion"

    @property
    def supported_scopes(self) -> tuple[str, ...]:
        return ("pages:read", "pages:write", "databases:read")

    def _register_actions(self) -> None:
        self._actions = {
            "read_page": ConnectorAction(
                name="read_page",
                action_type=ConnectorActionType.READ,
                required_scopes=("pages:read",),
            ),
            "search_database": ConnectorAction(
                name="search_database",
                action_type=ConnectorActionType.READ,
                required_scopes=("databases:read",),
            ),
            "create_page": ConnectorAction(
                name="create_page",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("pages:write",),
                requires_side_effect_confirmation=True,
            ),
            "update_page": ConnectorAction(
                name="update_page",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("pages:write",),
                requires_side_effect_confirmation=True,
            ),
        }

    def _perform_action(
        self, action_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        if action_name == "read_page":
            page_id = params.get("page_id", "page_123")
            return {"status": "success", "page_id": page_id, "title": "Notion Page"}
        if action_name == "search_database":
            return {"status": "success", "results": [{"id": "db_1", "name": "Tasks"}]}
        if action_name == "create_page":
            return {"status": "success", "page_id": "page_456", "created": True}
        if action_name == "update_page":
            return {"status": "success", "updated": True}
        return {}


class DriveConnector(BaseConnector):
    @property
    def connector_type(self) -> str:
        return "drive"

    @property
    def supported_scopes(self) -> tuple[str, ...]:
        return ("drive.readonly", "drive.file", "drive")

    def _register_actions(self) -> None:
        self._actions = {
            "get_file": ConnectorAction(
                name="get_file",
                action_type=ConnectorActionType.READ,
                required_scopes=("drive.readonly",),
            ),
            "list_files": ConnectorAction(
                name="list_files",
                action_type=ConnectorActionType.READ,
                required_scopes=("drive.readonly",),
            ),
            "upload_file": ConnectorAction(
                name="upload_file",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("drive.file",),
                requires_side_effect_confirmation=True,
            ),
            "delete_file": ConnectorAction(
                name="delete_file",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("drive",),
                requires_side_effect_confirmation=True,
            ),
        }

    def _perform_action(
        self, action_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        if action_name == "get_file":
            file_id = params.get("file_id", "file_1")
            return {"status": "success", "file_id": file_id, "name": "document.pdf"}
        if action_name == "list_files":
            return {"status": "success", "files": [{"id": "file_1", "name": "doc1.txt"}]}
        if action_name == "upload_file":
            filename = params.get("filename", "upload.txt")
            return {"status": "success", "file_id": "file_new", "filename": filename}
        if action_name == "delete_file":
            return {"status": "success", "deleted": True}
        return {}


class SlackConnector(BaseConnector):
    @property
    def connector_type(self) -> str:
        return "slack"

    @property
    def supported_scopes(self) -> tuple[str, ...]:
        return ("channels:read", "chat:write")

    def _register_actions(self) -> None:
        self._actions = {
            "read_messages": ConnectorAction(
                name="read_messages",
                action_type=ConnectorActionType.READ,
                required_scopes=("channels:read",),
            ),
            "list_channels": ConnectorAction(
                name="list_channels",
                action_type=ConnectorActionType.READ,
                required_scopes=("channels:read",),
            ),
            "send_message": ConnectorAction(
                name="send_message",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("chat:write",),
                requires_side_effect_confirmation=True,
            ),
        }

    def _perform_action(
        self, action_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        if action_name == "read_messages":
            channel = params.get("channel", "general")
            return {"status": "success", "channel": channel, "messages": ["Hello team"]}
        if action_name == "list_channels":
            return {"status": "success", "channels": ["general", "random"]}
        if action_name == "send_message":
            msg = params.get("message", "")
            return {"status": "success", "sent": True, "message": msg}
        return {}


class CalendarConnector(BaseConnector):
    @property
    def connector_type(self) -> str:
        return "calendar"

    @property
    def supported_scopes(self) -> tuple[str, ...]:
        return ("calendar.readonly", "calendar.events")

    def _register_actions(self) -> None:
        self._actions = {
            "list_events": ConnectorAction(
                name="list_events",
                action_type=ConnectorActionType.READ,
                required_scopes=("calendar.readonly",),
            ),
            "get_event": ConnectorAction(
                name="get_event",
                action_type=ConnectorActionType.READ,
                required_scopes=("calendar.readonly",),
            ),
            "create_event": ConnectorAction(
                name="create_event",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("calendar.events",),
                requires_side_effect_confirmation=True,
            ),
            "delete_event": ConnectorAction(
                name="delete_event",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("calendar.events",),
                requires_side_effect_confirmation=True,
            ),
        }

    def _perform_action(
        self, action_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        if action_name == "list_events":
            return {"status": "success", "events": [{"id": "evt_1", "summary": "Standup"}]}
        if action_name == "get_event":
            return {"status": "success", "event_id": "evt_1", "summary": "Standup"}
        if action_name == "create_event":
            summary = params.get("summary", "New Meeting")
            return {"status": "success", "event_id": "evt_new", "summary": summary}
        if action_name == "delete_event":
            return {"status": "success", "deleted": True}
        return {}


class EmailConnector(BaseConnector):
    @property
    def connector_type(self) -> str:
        return "email"

    @property
    def supported_scopes(self) -> tuple[str, ...]:
        return ("email:read", "email:send")

    def _register_actions(self) -> None:
        self._actions = {
            "read_emails": ConnectorAction(
                name="read_emails",
                action_type=ConnectorActionType.READ,
                required_scopes=("email:read",),
            ),
            "get_email": ConnectorAction(
                name="get_email",
                action_type=ConnectorActionType.READ,
                required_scopes=("email:read",),
            ),
            "send_email": ConnectorAction(
                name="send_email",
                action_type=ConnectorActionType.WRITE,
                required_scopes=("email:send",),
                requires_side_effect_confirmation=True,
            ),
        }

    def _perform_action(
        self, action_name: str, params: dict[str, Any]
    ) -> dict[str, Any]:
        if action_name == "read_emails":
            return {"status": "success", "emails": [{"id": "msg_1", "subject": "Welcome"}]}
        if action_name == "get_email":
            return {"status": "success", "email_id": "msg_1", "subject": "Welcome"}
        if action_name == "send_email":
            to = params.get("to", "user@example.com")
            subject = params.get("subject", "Hello")
            return {"status": "success", "sent": True, "to": to, "subject": subject}
        return {}
