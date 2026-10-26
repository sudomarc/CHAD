import time

import pytest

from chad.connectors import (
    CalendarConnector,
    ConnectorError,
    ConnectorRegistry,
    ConnectorType,
    EmailConnector,
    GitHubConnector,
    GoogleDriveConnector,
    NotionConnector,
    OAuthToken,
    ScopeError,
    SideEffectConfirmationRequiredError,
    SlackConnector,
    TokenExpiredError,
)


def test_oauth_token_expiration():
    token_valid = OAuthToken(access_token="tok123", expires_at=time.time() + 3600)
    assert not token_valid.is_expired()

    token_expired = OAuthToken(access_token="tok123", expires_at=time.time() - 100)
    assert token_expired.is_expired()


def test_connector_health_and_revocation():
    token = OAuthToken(access_token="gh_secret_token", scopes=("repo:read", "repo:write"))
    gh = GitHubConnector(connector_id="github_1", token=token)

    health = gh.check_health()
    assert health.connected is True
    assert health.status_message == "Healthy"

    # Revoke token
    gh.revoke_token()
    assert not gh.is_connected
    health_after = gh.check_health()
    assert health_after.connected is False
    assert "Disconnected" in health_after.status_message


def test_connector_scope_validation():
    # Token missing repo:write scope
    token = OAuthToken(access_token="gh_token", scopes=("repo:read",))
    gh = GitHubConnector(token=token)

    # Read action succeeds
    res_read = gh.execute_action("list_repos")
    assert res_read.success is True

    # Write action fails due to scope
    with pytest.raises(ScopeError):
        gh.execute_action("create_issue", side_effect_confirmed=True)


def test_connector_side_effect_confirmation():
    token = OAuthToken(access_token="gh_token", scopes=("repo:read", "repo:write"))
    gh = GitHubConnector(token=token)

    # Write action fails without side effect confirmation
    with pytest.raises(SideEffectConfirmationRequiredError):
        gh.execute_action("create_issue", params={"title": "Fix bug"})

    # Succeeds with confirmation
    res_write = gh.execute_action("create_issue", params={"title": "Fix bug"}, side_effect_confirmed=True)
    assert res_write.success is True
    assert res_write.side_effect_confirmed is True
    assert res_write.data["title"] == "Fix bug"


def test_token_expiration_error():
    expired_token = OAuthToken(access_token="exp", expires_at=time.time() - 10, scopes=("repo:read",))
    gh = GitHubConnector(token=expired_token)

    with pytest.raises(TokenExpiredError):
        gh.execute_action("list_repos")


def test_provider_connectors():
    # Notion
    notion_token = OAuthToken(access_token="notion_tok", scopes=("notion:read", "notion:write"))
    notion = NotionConnector(token=notion_token)
    assert notion.execute_action("query_database").success is True
    assert notion.execute_action("append_block", side_effect_confirmed=True).success is True

    # Google Drive
    drive_token = OAuthToken(access_token="drive_tok", scopes=("drive.readonly", "drive.file"))
    drive = GoogleDriveConnector(token=drive_token)
    assert drive.execute_action("search_files").success is True
    assert drive.execute_action("upload_file", params={"filename": "doc.txt"}, side_effect_confirmed=True).success is True

    # Slack
    slack_token = OAuthToken(access_token="slack_tok", scopes=("channels:history", "chat:write"))
    slack = SlackConnector(token=slack_token)
    assert slack.execute_action("read_messages").success is True
    assert slack.execute_action("post_message", params={"channel": "dev"}, side_effect_confirmed=True).success is True

    # Calendar
    cal_token = OAuthToken(access_token="cal_tok", scopes=("calendar.readonly", "calendar.events"))
    cal = CalendarConnector(token=cal_token)
    assert cal.execute_action("list_events").success is True
    assert cal.execute_action("create_event", params={"summary": "Demo"}, side_effect_confirmed=True).success is True

    # Email
    email_token = OAuthToken(access_token="email_tok", scopes=("mail.read", "mail.send"))
    email = EmailConnector(token=email_token)
    assert email.execute_action("fetch_emails").success is True
    assert email.execute_action("send_email", params={"to": "test@example.com"}, side_effect_confirmed=True).success is True


def test_connector_registry():
    registry = ConnectorRegistry()
    gh = GitHubConnector(connector_id="gh_1", token=OAuthToken("tok", scopes=("repo:read",)))
    notion = NotionConnector(connector_id="notion_1", token=OAuthToken("tok", scopes=("notion:read",)))

    registry.register(gh)
    registry.register(notion)

    assert registry.list_connectors() == ["gh_1", "notion_1"]
    assert registry.get("gh_1") == gh
    assert registry.list_by_type(ConnectorType.GITHUB) == [gh]

    health_summary = registry.check_all_health()
    assert "gh_1" in health_summary
    assert health_summary["gh_1"].connected is True

    registry.unregister("gh_1")
    assert registry.list_connectors() == ["notion_1"]

    with pytest.raises(ConnectorError):
        registry.get("gh_1")
