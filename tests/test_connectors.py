from __future__ import annotations

import time

import pytest

from chad.connectors import (
    CalendarConnector,
    ConnectorError,
    ConnectorRegistry,
    DriveConnector,
    EmailConnector,
    GitHubConnector,
    InsufficientScopeError,
    NotionConnector,
    OAuthToken,
    ScopeValidator,
    SideEffectConfirmationRequiredError,
    SlackConnector,
    TokenExpiredError,
    UnauthenticatedError,
)


def test_oauth_token_expiration() -> None:
    token = OAuthToken(
        access_token="test_access_token",
        expires_at=time.time() - 100,
        scopes=("repo:read",),
    )
    assert token.is_expired() is True

    valid_token = OAuthToken(
        access_token="test_access_token",
        expires_at=time.time() + 1000,
        scopes=("repo:read",),
    )
    assert valid_token.is_expired() is False


def test_scope_validator() -> None:
    granted = ("repo:read", "pages:read", "email:*")
    assert ScopeValidator.has_scope(granted, "repo:read") is True
    assert ScopeValidator.has_scope(granted, "email:send") is True
    assert ScopeValidator.has_scope(granted, "repo:write") is False

    ScopeValidator.validate_scopes(granted, ("repo:read", "pages:read"))
    with pytest.raises(InsufficientScopeError):
        ScopeValidator.validate_scopes(granted, ("repo:write",))


def test_connector_unauthenticated_and_expired() -> None:
    connector = GitHubConnector()
    assert connector.is_authenticated is False

    with pytest.raises(UnauthenticatedError):
        connector.execute("read_repo")

    expired_token = OAuthToken(
        access_token="tok",
        expires_at=time.time() - 10,
        scopes=("repo:read", "repo:write", "issue:write", "pr:write"),
    )
    connector.set_token(expired_token)
    assert connector.is_authenticated is False

    with pytest.raises(TokenExpiredError):
        connector.execute("read_repo")


def test_connector_read_write_and_side_effect_confirmation() -> None:
    connector = GitHubConnector()
    token = OAuthToken(
        access_token="valid_token",
        expires_at=time.time() + 3600,
        scopes=("repo:read", "issue:write"),
    )
    connector.set_token(token)
    assert connector.is_authenticated is True

    # READ action should succeed without confirmation
    read_res = connector.execute("read_repo", {"repo": "sudomarc/CHAD"})
    assert read_res["status"] == "success"
    assert read_res["repo"] == "sudomarc/CHAD"

    # WRITE action without confirmation should raise SideEffectConfirmationRequiredError
    with pytest.raises(SideEffectConfirmationRequiredError):
        connector.execute("create_issue", {"title": "Test Issue"}, confirmed=False)

    # WRITE action with confirmed=True should succeed
    write_res = connector.execute(
        "create_issue", {"title": "Test Issue"}, confirmed=True
    )
    assert write_res["status"] == "success"
    assert write_res["title"] == "Test Issue"


def test_connector_token_revocation_and_health() -> None:
    connector = SlackConnector()
    token = OAuthToken(
        access_token="slack_token",
        expires_at=time.time() + 3600,
        scopes=("channels:read", "chat:write"),
    )
    connector.set_token(token)

    health = connector.check_health()
    assert health.status == "healthy"
    assert "Slack" in health.message

    revoked = connector.revoke_token()
    assert revoked is True
    assert connector.token is None

    unhealthy = connector.check_health()
    assert unhealthy.status == "unhealthy"


def test_all_provider_connectors() -> None:
    providers = [
        (GitHubConnector, ("repo:read", "issue:write"), "read_repo", "create_issue"),
        (
            NotionConnector,
            ("pages:read", "pages:write"),
            "read_page",
            "create_page",
        ),
        (
            DriveConnector,
            ("drive.readonly", "drive.file"),
            "get_file",
            "upload_file",
        ),
        (
            SlackConnector,
            ("channels:read", "chat:write"),
            "read_messages",
            "send_message",
        ),
        (
            CalendarConnector,
            ("calendar.readonly", "calendar.events"),
            "list_events",
            "create_event",
        ),
        (EmailConnector, ("email:read", "email:send"), "read_emails", "send_email"),
    ]

    for connector_cls, scopes, read_act, write_act in providers:
        conn = connector_cls()
        token = OAuthToken(
            access_token="tok_123",
            expires_at=time.time() + 3600,
            scopes=scopes,
        )
        conn.set_token(token)

        # Read action
        read_out = conn.execute(read_act)
        assert read_out["status"] == "success"

        # Write action without confirmation raises
        with pytest.raises(SideEffectConfirmationRequiredError):
            conn.execute(write_act, confirmed=False)

        # Write action with confirmation succeeds
        write_out = conn.execute(write_act, confirmed=True)
        assert write_out["status"] == "success"


def test_connector_registry() -> None:
    registry = ConnectorRegistry()
    gh = GitHubConnector()
    slack = SlackConnector()

    registry.register(gh)
    registry.register(slack)

    assert len(registry.list_connectors()) == 2
    assert registry.get("github") is gh
    assert registry.get("slack") is slack

    health_map = registry.check_all_health()
    assert "github" in health_map
    assert "slack" in health_map

    registry.unregister("github")
    assert len(registry.list_connectors()) == 1
    with pytest.raises(ConnectorError):
        registry.get("github")
