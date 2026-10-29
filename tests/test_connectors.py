import time
import pytest

from chad.connectors import (
    AuthenticationError,
    CalendarConnector,
    ConnectorHealth,
    ConnectorOperation,
    ConnectorOperationType,
    ConnectorRegistry,
    ConnectorStatus,
    ConnectorType,
    DriveConnector,
    EmailConnector,
    GitHubConnector,
    InsufficientScopeError,
    NotionConnector,
    OAuthToken,
    SideEffectConfirmationRequiredError,
    SlackConnector,
)


def test_oauth_token_and_revocation():
    token = OAuthToken(
        access_token="gho_test123",
        scopes=("repo", "read:user"),
        expires_at=time.time() + 3600,
    )
    connector = GitHubConnector()
    assert not connector.is_authenticated()

    connector.authenticate(token)
    assert connector.is_authenticated()
    assert connector.token == token

    connector.revoke()
    assert not connector.is_authenticated()
    assert connector.token is None


def test_scope_validation():
    connector = NotionConnector()
    token = OAuthToken(
        access_token="ntn_test123",
        scopes=("pages:read",),
    )

    with pytest.raises(AuthenticationError):
        connector.validate_scopes("pages:read")

    connector.authenticate(token)
    connector.validate_scopes("pages:read")

    with pytest.raises(InsufficientScopeError):
        connector.validate_scopes("pages:write")


def test_read_write_separation_and_side_effect_confirmation():
    connector = SlackConnector()
    token = OAuthToken(
        access_token="xoxb-test",
        scopes=("channels:read", "chat:write"),
    )
    connector.authenticate(token)

    read_op = ConnectorOperation(
        operation_id="slack_read_1",
        connector_type=ConnectorType.SLACK,
        operation_type=ConnectorOperationType.READ,
        required_scope="channels:read",
        payload={"channel": "general"},
    )
    read_res = connector.execute_operation(read_op)
    assert read_res["status"] == "success"
    assert read_res["type"] == "read"

    write_op = ConnectorOperation(
        operation_id="slack_write_1",
        connector_type=ConnectorType.SLACK,
        operation_type=ConnectorOperationType.WRITE,
        required_scope="chat:write",
        payload={"text": "Hello world"},
        requires_side_effect_confirmation=True,
    )

    with pytest.raises(SideEffectConfirmationRequiredError):
        connector.execute_operation(write_op, confirmed=False)

    write_res = connector.execute_operation(write_op, confirmed=True)
    assert write_res["status"] == "success"
    assert write_res["type"] == "write"


def test_health_checks():
    connector = DriveConnector()
    health_disc = connector.health_check()
    assert not health_disc.healthy
    assert health_disc.status == ConnectorStatus.DISCONNECTED

    expired_token = OAuthToken(
        access_token="expired_tok",
        expires_at=time.time() - 10,
    )
    connector.authenticate(expired_token)
    health_exp = connector.health_check()
    assert not health_exp.healthy
    assert health_exp.status == ConnectorStatus.EXPIRED

    valid_token = OAuthToken(
        access_token="valid_tok",
        expires_at=time.time() + 3600,
    )
    connector.authenticate(valid_token)
    health_ok = connector.health_check()
    assert health_ok.healthy
    assert health_ok.status == ConnectorStatus.AUTHENTICATED


def test_connector_registry_operations():
    registry = ConnectorRegistry()

    gh = GitHubConnector()
    slack = SlackConnector()
    cal = CalendarConnector()

    registry.register(gh)
    registry.register(slack)
    registry.register(cal)

    assert registry.is_registered("github")
    assert registry.is_registered("slack")
    assert registry.is_registered(ConnectorType.CALENDAR)
    assert not registry.is_registered(ConnectorType.EMAIL)
    assert len(registry.list_connectors()) == 3

    token_gh = OAuthToken(
        access_token="gh_token",
        scopes=("repo",),
    )
    registry.authenticate("github", token_gh)
    assert gh.is_authenticated()

    health_all = registry.health_check_all()
    assert health_all["github"].healthy
    assert not health_all["slack"].healthy

    op = ConnectorOperation(
        operation_id="email_send_1",
        connector_type=ConnectorType.EMAIL,
        operation_type=ConnectorOperationType.READ,
        required_scope="mail:read",
        payload={"folder": "inbox"},
    )

    with pytest.raises(KeyError):
        registry.execute_operation(op)

    email = EmailConnector()
    registry.register(email)
    registry.authenticate("email", OAuthToken(access_token="email_tok", scopes=("mail:read",)))
    res = registry.execute_operation(op)
    assert res["status"] == "success"

    registry.revoke("github")
    assert not gh.is_authenticated()
