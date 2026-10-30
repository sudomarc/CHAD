from __future__ import annotations

import time

import pytest

from chad.connectors import (
    AuthError,
    CalendarConnector,
    ConnectorError,
    ConnectorRegistry,
    ConnectorRevokedError,
    DriveConnector,
    EmailConnector,
    GitHubConnector,
    NotionConnector,
    OAuthToken,
    OperationType,
    ScopeError,
    SideEffectDeniedError,
    SlackConnector,
)


def test_oauth_token_expiration_and_scopes() -> None:
    now = time.time()
    valid_token = OAuthToken(
        access_token="valid_secret",
        expires_at=now + 3600,
        scopes={"repo:read", "repo:write"},
    )
    assert not valid_token.is_expired(now)
    assert valid_token.has_scope("repo:read")
    assert not valid_token.has_scope("admin:all")

    expired_token = OAuthToken(
        access_token="expired_secret",
        expires_at=now - 100,
        scopes={"*"},
    )
    assert expired_token.is_expired(now)
    assert expired_token.has_scope("anything")


def test_connector_authentication_and_revocation() -> None:
    connector = GitHubConnector()
    assert connector.token is None
    assert not connector.is_revoked

    health_unauth = connector.health_check()
    assert health_unauth.status == "unauthenticated"

    token = OAuthToken(access_token="gh_token", scopes={"repo:read", "repo:write"})
    connector.authenticate(token)
    assert connector.token == token
    assert connector.health_check().status == "healthy"

    connector.revoke()
    assert connector.is_revoked
    assert connector.token is None
    assert connector.health_check().status == "revoked"


def test_connector_expired_health() -> None:
    connector = NotionConnector()
    expired_token = OAuthToken(access_token="token", expires_at=time.time() - 10, scopes={"page:read"})
    connector.authenticate(expired_token)
    assert connector.health_check().status == "unhealthy"


def test_scope_and_auth_validation_errors() -> None:
    connector = GitHubConnector()
    with pytest.raises(AuthError, match="not authenticated"):
        connector.execute("list_repos", OperationType.READ)

    read_token = OAuthToken(access_token="gh_token", scopes={"repo:read"})
    connector.authenticate(read_token)

    # Read succeeds
    res = connector.execute("list_repos", OperationType.READ)
    assert res["status"] == "success"

    # Write fails due to missing scope
    with pytest.raises(ScopeError, match="repo:write"):
        connector.execute("create_issue", OperationType.WRITE, confirmed=True)


def test_side_effect_confirmation_enforcement() -> None:
    connector = SlackConnector()
    token = OAuthToken(access_token="slack_token", scopes={"slack:read", "slack:write"})
    connector.authenticate(token)

    # Read requires no confirmation
    res_read = connector.execute("list_channels", OperationType.READ)
    assert res_read["status"] == "success"

    # Write without confirmation raises error
    with pytest.raises(SideEffectDeniedError, match="explicit side-effect confirmation"):
        connector.execute("post_message", OperationType.WRITE, confirmed=False)

    # Write with confirmation succeeds
    res_write = connector.execute("post_message", OperationType.WRITE, confirmed=True)
    assert res_write["status"] == "success"


def test_all_services_execution() -> None:
    connectors = [
        (GitHubConnector(), "list_repos", "create_issue", "repo:read", "repo:write"),
        (NotionConnector(), "get_page", "create_page", "page:read", "page:write"),
        (DriveConnector(), "list_files", "upload_file", "drive:read", "drive:write"),
        (SlackConnector(), "list_channels", "post_message", "slack:read", "slack:write"),
        (CalendarConnector(), "list_events", "create_event", "calendar:read", "calendar:write"),
        (EmailConnector(), "list_emails", "send_email", "email:read", "email:write"),
    ]

    for conn, read_op, write_op, read_scope, write_scope in connectors:
        token = OAuthToken(access_token=f"{conn.service_name}_tok", scopes={read_scope, write_scope})
        conn.authenticate(token)

        read_res = conn.execute(read_op, OperationType.READ)
        assert read_res["status"] == "success"
        assert read_res["service"] == conn.service_name

        write_res = conn.execute(write_op, OperationType.WRITE, confirmed=True)
        assert write_res["status"] == "success"
        assert write_res["service"] == conn.service_name

        # Invalid operation
        with pytest.raises(ConnectorError, match="Unsupported operation"):
            conn.execute("unknown_op", OperationType.READ)


def test_connector_registry() -> None:
    registry = ConnectorRegistry()
    gh = GitHubConnector()
    notion = NotionConnector()

    registry.register(gh)
    registry.register(notion)

    assert set(registry.list_connectors()) == {"github", "notion"}
    assert registry.get("github") == gh

    health_all = registry.health_check_all()
    assert health_all["github"].status == "unauthenticated"
    assert health_all["notion"].status == "unauthenticated"

    registry.revoke_all()
    assert gh.is_revoked
    assert notion.is_revoked

    registry.unregister("github")
    assert "github" not in registry.list_connectors()

    with pytest.raises(ConnectorError, match="not registered"):
        registry.get("github")
