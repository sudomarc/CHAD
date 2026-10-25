from __future__ import annotations

from typing import Any, ClassVar

from chad.connectors.base import (
    BaseConnector,
    ConnectorAccessLevel,
    ConnectorScope,
    ConnectorStatus,
    OperationMetadata,
)


class GitHubConnector(BaseConnector):
    """Connector for GitHub API integration."""

    SCOPES: ClassVar[tuple[ConnectorScope, ...]] = (
        ConnectorScope("repo:read", "Read repository contents and metadata", ConnectorAccessLevel.READ),
        ConnectorScope("issues:write", "Create and modify issues", ConnectorAccessLevel.WRITE),
        ConnectorScope("pull_requests:write", "Create and modify pull requests", ConnectorAccessLevel.WRITE),
    )

    OPERATIONS: ClassVar[dict[str, OperationMetadata]] = {
        "read_repo": OperationMetadata(
            name="read_repo",
            description="Read GitHub repository details and files",
            access_level=ConnectorAccessLevel.READ,
            required_scopes=("repo:read",),
            has_side_effect=False,
        ),
        "create_issue": OperationMetadata(
            name="create_issue",
            description="Create a new GitHub issue",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("issues:write",),
            has_side_effect=True,
        ),
        "create_pull_request": OperationMetadata(
            name="create_pull_request",
            description="Create a new GitHub pull request",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("pull_requests:write",),
            has_side_effect=True,
        ),
    }

    def __init__(self, connector_id: str = "github_default", name: str = "GitHub") -> None:
        super().__init__(connector_id, name, "github", self.SCOPES)

    def get_operations(self) -> dict[str, OperationMetadata]:
        return self.OPERATIONS

    def health_check(self) -> bool:
        return self.status == ConnectorStatus.CONNECTED

    def execute_operation(
        self,
        operation_name: str,
        params: dict | None = None,
        confirm_side_effects: bool = False,
    ) -> dict[str, Any]:
        params = params or {}
        op_meta = self.check_operation_permissions(operation_name, confirm_side_effects)

        if operation_name == "read_repo":
            repo = params.get("repo", "sudomarc/CHAD")
            return {"status": "success", "repo": repo, "stars": 42, "description": "CHAD AI Agent Runtime"}
        elif operation_name == "create_issue":
            title = params.get("title", "Untitled Issue")
            return {"status": "created", "issue_id": 101, "title": title, "url": f"https://github.com/{params.get('repo', 'sudomarc/CHAD')}/issues/101"}
        elif operation_name == "create_pull_request":
            title = params.get("title", "Untitled PR")
            return {"status": "created", "pr_id": 12, "title": title, "url": f"https://github.com/{params.get('repo', 'sudomarc/CHAD')}/pull/12"}

        return {"status": "success", "operation": op_meta.name}


class NotionConnector(BaseConnector):
    """Connector for Notion workspace API integration."""

    SCOPES: ClassVar[tuple[ConnectorScope, ...]] = (
        ConnectorScope("pages:read", "Read Notion pages and databases", ConnectorAccessLevel.READ),
        ConnectorScope("pages:write", "Create and update Notion pages", ConnectorAccessLevel.WRITE),
    )

    OPERATIONS: ClassVar[dict[str, OperationMetadata]] = {
        "read_page": OperationMetadata(
            name="read_page",
            description="Read contents of a Notion page",
            access_level=ConnectorAccessLevel.READ,
            required_scopes=("pages:read",),
            has_side_effect=False,
        ),
        "search_pages": OperationMetadata(
            name="search_pages",
            description="Search pages in Notion workspace",
            access_level=ConnectorAccessLevel.READ,
            required_scopes=("pages:read",),
            has_side_effect=False,
        ),
        "create_page": OperationMetadata(
            name="create_page",
            description="Create a new Notion page",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("pages:write",),
            has_side_effect=True,
        ),
        "update_page": OperationMetadata(
            name="update_page",
            description="Update an existing Notion page",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("pages:write",),
            has_side_effect=True,
        ),
    }

    def __init__(self, connector_id: str = "notion_default", name: str = "Notion") -> None:
        super().__init__(connector_id, name, "notion", self.SCOPES)

    def get_operations(self) -> dict[str, OperationMetadata]:
        return self.OPERATIONS

    def health_check(self) -> bool:
        return self.status == ConnectorStatus.CONNECTED

    def execute_operation(
        self,
        operation_name: str,
        params: dict | None = None,
        confirm_side_effects: bool = False,
    ) -> dict[str, Any]:
        params = params or {}
        op_meta = self.check_operation_permissions(operation_name, confirm_side_effects)

        if operation_name == "read_page":
            page_id = params.get("page_id", "page_123")
            return {"status": "success", "page_id": page_id, "title": "Architecture Spec", "blocks": []}
        elif operation_name == "search_pages":
            query = params.get("query", "")
            return {"status": "success", "query": query, "results": [{"id": "page_123", "title": "Architecture Spec"}]}
        elif operation_name == "create_page":
            title = params.get("title", "New Note")
            return {"status": "created", "page_id": "page_999", "title": title}
        elif operation_name == "update_page":
            page_id = params.get("page_id", "page_123")
            return {"status": "updated", "page_id": page_id}

        return {"status": "success", "operation": op_meta.name}


class DriveConnector(BaseConnector):
    """Connector for Google Drive storage integration."""

    SCOPES: ClassVar[tuple[ConnectorScope, ...]] = (
        ConnectorScope("drive.readonly", "Read files and metadata from Google Drive", ConnectorAccessLevel.READ),
        ConnectorScope("drive.file", "Create, update, and delete files in Google Drive", ConnectorAccessLevel.WRITE),
    )

    OPERATIONS: ClassVar[dict[str, OperationMetadata]] = {
        "list_files": OperationMetadata(
            name="list_files",
            description="List files in Google Drive directory",
            access_level=ConnectorAccessLevel.READ,
            required_scopes=("drive.readonly",),
            has_side_effect=False,
        ),
        "read_file": OperationMetadata(
            name="read_file",
            description="Read file contents from Google Drive",
            access_level=ConnectorAccessLevel.READ,
            required_scopes=("drive.readonly",),
            has_side_effect=False,
        ),
        "upload_file": OperationMetadata(
            name="upload_file",
            description="Upload a new file to Google Drive",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("drive.file",),
            has_side_effect=True,
        ),
        "delete_file": OperationMetadata(
            name="delete_file",
            description="Delete a file from Google Drive",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("drive.file",),
            has_side_effect=True,
        ),
    }

    def __init__(self, connector_id: str = "drive_default", name: str = "Google Drive") -> None:
        super().__init__(connector_id, name, "drive", self.SCOPES)

    def get_operations(self) -> dict[str, OperationMetadata]:
        return self.OPERATIONS

    def health_check(self) -> bool:
        return self.status == ConnectorStatus.CONNECTED

    def execute_operation(
        self,
        operation_name: str,
        params: dict | None = None,
        confirm_side_effects: bool = False,
    ) -> dict[str, Any]:
        params = params or {}
        op_meta = self.check_operation_permissions(operation_name, confirm_side_effects)

        if operation_name == "list_files":
            return {"status": "success", "files": [{"file_id": "f1", "filename": "roadmap.pdf"}]}
        elif operation_name == "read_file":
            file_id = params.get("file_id", "f1")
            return {"status": "success", "file_id": file_id, "content": "Sample file content"}
        elif operation_name == "upload_file":
            filename = params.get("filename", "document.txt")
            return {"status": "uploaded", "file_id": "f200", "filename": filename}
        elif operation_name == "delete_file":
            file_id = params.get("file_id", "f1")
            return {"status": "deleted", "file_id": file_id}

        return {"status": "success", "operation": op_meta.name}


class SlackConnector(BaseConnector):
    """Connector for Slack messaging integration."""

    SCOPES: ClassVar[tuple[ConnectorScope, ...]] = (
        ConnectorScope("channels:read", "Read Slack channels and public message history", ConnectorAccessLevel.READ),
        ConnectorScope("chat:write", "Post messages to Slack channels", ConnectorAccessLevel.WRITE),
    )

    OPERATIONS: ClassVar[dict[str, OperationMetadata]] = {
        "read_channel": OperationMetadata(
            name="read_channel",
            description="Read message history from a Slack channel",
            access_level=ConnectorAccessLevel.READ,
            required_scopes=("channels:read",),
            has_side_effect=False,
        ),
        "send_message": OperationMetadata(
            name="send_message",
            description="Post a message to a Slack channel",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("chat:write",),
            has_side_effect=True,
        ),
    }

    def __init__(self, connector_id: str = "slack_default", name: str = "Slack") -> None:
        super().__init__(connector_id, name, "slack", self.SCOPES)

    def get_operations(self) -> dict[str, OperationMetadata]:
        return self.OPERATIONS

    def health_check(self) -> bool:
        return self.status == ConnectorStatus.CONNECTED

    def execute_operation(
        self,
        operation_name: str,
        params: dict | None = None,
        confirm_side_effects: bool = False,
    ) -> dict[str, Any]:
        params = params or {}
        op_meta = self.check_operation_permissions(operation_name, confirm_side_effects)

        if operation_name == "read_channel":
            channel = params.get("channel", "general")
            return {"status": "success", "channel": channel, "messages": [{"user": "U1", "text": "Hello CHAD!"}]}
        elif operation_name == "send_message":
            channel = params.get("channel", "general")
            text = params.get("text", "")
            return {"status": "sent", "channel": channel, "message_ts": "1710000000.000100", "text": text}

        return {"status": "success", "operation": op_meta.name}


class CalendarConnector(BaseConnector):
    """Connector for Calendar event integration."""

    SCOPES: ClassVar[tuple[ConnectorScope, ...]] = (
        ConnectorScope("calendar.readonly", "View calendar events and schedules", ConnectorAccessLevel.READ),
        ConnectorScope("calendar.events", "Create and cancel calendar events", ConnectorAccessLevel.WRITE),
    )

    OPERATIONS: ClassVar[dict[str, OperationMetadata]] = {
        "list_events": OperationMetadata(
            name="list_events",
            description="List scheduled calendar events",
            access_level=ConnectorAccessLevel.READ,
            required_scopes=("calendar.readonly",),
            has_side_effect=False,
        ),
        "create_event": OperationMetadata(
            name="create_event",
            description="Schedule a new calendar event",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("calendar.events",),
            has_side_effect=True,
        ),
        "cancel_event": OperationMetadata(
            name="cancel_event",
            description="Cancel an existing calendar event",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("calendar.events",),
            has_side_effect=True,
        ),
    }

    def __init__(self, connector_id: str = "calendar_default", name: str = "Google Calendar") -> None:
        super().__init__(connector_id, name, "calendar", self.SCOPES)

    def get_operations(self) -> dict[str, OperationMetadata]:
        return self.OPERATIONS

    def health_check(self) -> bool:
        return self.status == ConnectorStatus.CONNECTED

    def execute_operation(
        self,
        operation_name: str,
        params: dict | None = None,
        confirm_side_effects: bool = False,
    ) -> dict[str, Any]:
        params = params or {}
        op_meta = self.check_operation_permissions(operation_name, confirm_side_effects)

        if operation_name == "list_events":
            return {"status": "success", "events": [{"event_id": "e1", "summary": "CHAD Sync Meeting"}]}
        elif operation_name == "create_event":
            summary = params.get("summary", "New Event")
            return {"status": "created", "event_id": "e500", "summary": summary}
        elif operation_name == "cancel_event":
            event_id = params.get("event_id", "e1")
            return {"status": "cancelled", "event_id": event_id}

        return {"status": "success", "operation": op_meta.name}


class EmailConnector(BaseConnector):
    """Connector for Email service integration (Gmail/SMTP/IMAP)."""

    SCOPES: ClassVar[tuple[ConnectorScope, ...]] = (
        ConnectorScope("mail.read", "Read inbox emails and threads", ConnectorAccessLevel.READ),
        ConnectorScope("mail.send", "Send emails to external recipients", ConnectorAccessLevel.WRITE),
    )

    OPERATIONS: ClassVar[dict[str, OperationMetadata]] = {
        "read_emails": OperationMetadata(
            name="read_emails",
            description="Read unread or queried emails",
            access_level=ConnectorAccessLevel.READ,
            required_scopes=("mail.read",),
            has_side_effect=False,
        ),
        "send_email": OperationMetadata(
            name="send_email",
            description="Send an email to specified recipients",
            access_level=ConnectorAccessLevel.WRITE,
            required_scopes=("mail.send",),
            has_side_effect=True,
        ),
    }

    def __init__(self, connector_id: str = "email_default", name: str = "Email") -> None:
        super().__init__(connector_id, name, "email", self.SCOPES)

    def get_operations(self) -> dict[str, OperationMetadata]:
        return self.OPERATIONS

    def health_check(self) -> bool:
        return self.status == ConnectorStatus.CONNECTED

    def execute_operation(
        self,
        operation_name: str,
        params: dict | None = None,
        confirm_side_effects: bool = False,
    ) -> dict[str, Any]:
        params = params or {}
        op_meta = self.check_operation_permissions(operation_name, confirm_side_effects)

        if operation_name == "read_emails":
            query = params.get("query", "is:unread")
            return {"status": "success", "query": query, "emails": [{"id": "m100", "subject": "Update on CHAD"}]}
        elif operation_name == "send_email":
            to = params.get("to", "recipient@example.com")
            subject = params.get("subject", "No subject")
            return {"status": "sent", "email_id": "m500", "to": to, "subject": subject}

        return {"status": "success", "operation": op_meta.name}
