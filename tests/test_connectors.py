import time

import pytest

from chad.connectors import (
    CalendarConnector,
    ConnectorRegistry,
    ConnectorStatus,
    DriveConnector,
    EmailConnector,
    GitHubConnector,
    NotionConnector,
    OAuthScopeError,
    OAuthToken,
    SideEffectConfirmationRequiredError,
    SlackConnector,
)


def test_oauth_token_and_status() -> None:
    token = OAuthToken(access_token="tok123", scopes=("repo:read",))
    assert not token.is_expired()

    expired_token = OAuthToken(access_token="tok123", expires_at=time.time() - 10)
    assert expired_token.is_expired()

    gh = GitHubConnector()
    assert gh.status == ConnectorStatus.DISCONNECTED

    gh.connect(expired_token)
    assert gh.status == ConnectorStatus.EXPIRED

    gh.connect(token)
    assert gh.status == ConnectorStatus.CONNECTED

    gh.revoke()
    assert gh.status == ConnectorStatus.REVOKED
    assert gh.token is None


def test_scope_validation() -> None:
    gh = GitHubConnector()
    token_empty = OAuthToken(access_token="tok_empty", scopes=())
    gh.connect(token_empty)

    with pytest.raises(OAuthScopeError) as exc_info_empty:
        gh.execute_operation("read_repo", {"repo": "sudomarc/CHAD"})
    assert "repo:read" in str(exc_info_empty.value)

    token_limited = OAuthToken(access_token="tok_read", scopes=("repo:read",))
    gh.connect(token_limited)

    # Read repo requires 'repo:read' which is present
    res = gh.execute_operation("read_repo", {"repo": "sudomarc/CHAD"})
    assert res["status"] == "success"

    # Create issue requires 'issues:write' which is missing
    with pytest.raises(OAuthScopeError) as exc_info:
        gh.execute_operation("create_issue", {"title": "Bug"}, confirm_side_effects=True)
    assert "issues:write" in str(exc_info.value)


def test_side_effect_confirmation_requirement() -> None:
    gh = GitHubConnector()
    full_token = OAuthToken(access_token="tok_full", scopes=("repo:read", "issues:write", "pull_requests:write"))
    gh.connect(full_token)

    # Calling write operation without confirmation raises error
    with pytest.raises(SideEffectConfirmationRequiredError) as exc_info:
        gh.execute_operation("create_issue", {"title": "Test Issue"}, confirm_side_effects=False)
    assert exc_info.value.operation == "create_issue"
    assert exc_info.value.connector_id == "github_default"

    # Calling write operation with confirmation succeeds
    res = gh.execute_operation("create_issue", {"title": "Test Issue"}, confirm_side_effects=True)
    assert res["status"] == "created"
    assert res["issue_id"] == 101


def test_github_connector_operations() -> None:
    gh = GitHubConnector()
    gh.connect(OAuthToken(access_token="tok", scopes=("repo:read", "issues:write", "pull_requests:write")))

    repo_res = gh.execute_operation("read_repo")
    assert repo_res["repo"] == "sudomarc/CHAD"

    pr_res = gh.execute_operation("create_pull_request", {"title": "New Feat"}, confirm_side_effects=True)
    assert pr_res["status"] == "created"
    assert pr_res["pr_id"] == 12


def test_notion_connector_operations() -> None:
    notion = NotionConnector()
    notion.connect(OAuthToken(access_token="tok_notion", scopes=("pages:read", "pages:write")))

    page_res = notion.execute_operation("read_page", {"page_id": "p123"})
    assert page_res["page_id"] == "p123"

    search_res = notion.execute_operation("search_pages", {"query": "spec"})
    assert len(search_res["results"]) > 0

    create_res = notion.execute_operation("create_page", {"title": "Docs"}, confirm_side_effects=True)
    assert create_res["status"] == "created"

    update_res = notion.execute_operation("update_page", {"page_id": "p123"}, confirm_side_effects=True)
    assert update_res["status"] == "updated"


def test_drive_connector_operations() -> None:
    drive = DriveConnector()
    drive.connect(OAuthToken(access_token="tok_drive", scopes=("drive.readonly", "drive.file")))

    files = drive.execute_operation("list_files")
    assert len(files["files"]) == 1

    content = drive.execute_operation("read_file", {"file_id": "f1"})
    assert content["status"] == "success"

    upload = drive.execute_operation("upload_file", {"filename": "doc.pdf"}, confirm_side_effects=True)
    assert upload["status"] == "uploaded"

    delete = drive.execute_operation("delete_file", {"file_id": "f1"}, confirm_side_effects=True)
    assert delete["status"] == "deleted"


def test_slack_connector_operations() -> None:
    slack = SlackConnector()
    slack.connect(OAuthToken(access_token="tok_slack", scopes=("channels:read", "chat:write")))

    read_res = slack.execute_operation("read_channel", {"channel": "dev"})
    assert read_res["channel"] == "dev"

    send_res = slack.execute_operation("send_message", {"channel": "dev", "text": "Hi!"}, confirm_side_effects=True)
    assert send_res["status"] == "sent"


def test_calendar_connector_operations() -> None:
    cal = CalendarConnector()
    cal.connect(OAuthToken(access_token="tok_cal", scopes=("calendar.readonly", "calendar.events")))

    events = cal.execute_operation("list_events")
    assert len(events["events"]) == 1

    create = cal.execute_operation("create_event", {"summary": "Standup"}, confirm_side_effects=True)
    assert create["status"] == "created"

    cancel = cal.execute_operation("cancel_event", {"event_id": "e1"}, confirm_side_effects=True)
    assert cancel["status"] == "cancelled"


def test_email_connector_operations() -> None:
    email = EmailConnector()
    email.connect(OAuthToken(access_token="tok_email", scopes=("mail.read", "mail.send")))

    inbox = email.execute_operation("read_emails")
    assert len(inbox["emails"]) == 1

    send = email.execute_operation("send_email", {"to": "user@test.com", "subject": "Hello"}, confirm_side_effects=True)
    assert send["status"] == "sent"


def test_connector_registry() -> None:
    registry = ConnectorRegistry()
    gh = GitHubConnector()
    notion = NotionConnector()

    registry.register(gh)
    registry.register(notion)

    assert registry.get("github_default") == gh
    assert len(registry.get_by_type("github")) == 1
    assert len(registry.list_connectors()) == 2

    health = registry.health_check_all()
    assert health["github_default"] is False  # Not connected

    gh.connect(OAuthToken("tok_gh", scopes=("repo:read", "issues:write", "pull_requests:write")))
    notion.connect(OAuthToken("tok_n", scopes=("pages:read", "pages:write")))

    assert registry.health_check_all()["github_default"] is True

    # Execute via registry
    res = registry.execute_operation("github_default", "read_repo")
    assert res["status"] == "success"

    # Generate tools
    tools = registry.generate_tools()
    assert len(tools) > 0
    gh_tools = [t for t in tools if t.id.startswith("connector_github_default")]
    assert len(gh_tools) == 3

    # Revoke via registry
    registry.revoke("github_default")
    assert gh.status == ConnectorStatus.REVOKED

    # Unregister
    assert registry.unregister("github_default") is True
    assert registry.get("github_default") is None
