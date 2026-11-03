from __future__ import annotations

import json
import threading
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from chad.app import ChadApp
from chad.auth.engine import AuthEngine, hash_password, verify_password
from chad.auth.lifecycle import AccountLifecycleManager
from chad.auth.models import (
    AccessDeniedError,
    InvalidCredentialsError,
    Permission,
    QuotaLimits,
    RateLimitExceededError,
    SessionExpiredError,
    StorageQuotaExceededError,
    TokenQuotaExceededError,
    User,
    UserAlreadyExistsError,
    UserNotFoundError,
    UserRole,
    UserTier,
)
from chad.auth.ownership import DataOwnershipManager
from chad.auth.quotas import QuotaManager
from chad.auth.sessions import SessionManager
from chad.core.config import AppConfig
from chad.core.conversation import ChatRequest, Conversation
from chad.interfaces.web import create_web_server
from chad.llm.client import LapisClient, ModelInfo


class DummyLapisClient(LapisClient):
    def generate(self, request: ChatRequest) -> str:
        return f"Echo: {request.messages[-1].content}"

    def current_model(self) -> ModelInfo:
        return ModelInfo(id="dummy-model", display_name="Dummy Model")


def _http_request(
    url: str,
    method: str = "GET",
    data: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    req = urllib.request.Request(url, method=method)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    if data is not None:
        payload = json.dumps(data).encode("utf-8")
        req.add_header("Content-Type", "application/json")
        req.data = payload

    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            body = json.loads(resp.read().decode("utf-8"))
            return status, body
    except urllib.error.HTTPError as err:
        body = json.loads(err.read().decode("utf-8"))
        return err.code, body


# 1. Tests for Password hashing & AuthEngine
def test_password_hashing() -> None:
    password = "SuperSecretPassword123!"
    hashed = hash_password(password)
    assert verify_password(password, hashed) is True
    assert verify_password("WrongPassword", hashed) is False
    assert verify_password("", hashed) is False


def test_auth_engine_user_registration_and_authentication() -> None:
    engine = AuthEngine()
    user = engine.register_user(
        username="alice",
        email="alice@example.com",
        password="AlicePassword123!",
        role=UserRole.MEMBER,
        tier=UserTier.PRO,
    )
    assert user.id is not None
    assert user.username == "alice"
    assert user.role == UserRole.MEMBER
    assert user.tier == UserTier.PRO

    # Authenticate with username
    auth_user = engine.authenticate_password("alice", "AlicePassword123!")
    assert auth_user.id == user.id

    # Authenticate with email
    auth_user2 = engine.authenticate_password("alice@example.com", "AlicePassword123!")
    assert auth_user2.id == user.id

    # Wrong password
    with pytest.raises(InvalidCredentialsError):
        engine.authenticate_password("alice", "WrongPassword")

    # Duplicate registration
    with pytest.raises(UserAlreadyExistsError):
        engine.register_user(username="alice", email="other@example.com", password="pwd")
    with pytest.raises(UserAlreadyExistsError):
        engine.register_user(username="other", email="alice@example.com", password="pwd")


def test_auth_engine_api_keys() -> None:
    engine = AuthEngine()
    user = engine.register_user("bob", "bob@example.com", "BobPwd123!")
    record, raw_key = engine.create_api_key(user.id, label="Bob CLI Key")

    assert raw_key.startswith("chad_live_")
    assert record.user_id == user.id
    assert record.is_revoked is False

    # Authenticate with API key
    auth_user, rec = engine.authenticate_api_key(raw_key)
    assert auth_user.id == user.id
    assert rec.id == record.id

    # Revoke key
    engine.revoke_api_key(record.id)
    with pytest.raises(AccessDeniedError, match="revoked"):
        engine.authenticate_api_key(raw_key)


def test_auth_engine_rbac_permissions() -> None:
    engine = AuthEngine()
    admin = engine.register_user("admin", "admin@chad.ai", "admin123", role=UserRole.ADMIN)
    member = engine.register_user("member", "member@chad.ai", "member123", role=UserRole.MEMBER)
    guest = engine.register_user("guest", "guest@chad.ai", "guest123", role=UserRole.GUEST)

    # Admin has all permissions
    assert engine.has_permission(admin, Permission.USER_MANAGE) is True
    assert engine.has_permission(admin, Permission.ADMIN_CONFIG) is True
    assert engine.has_permission(admin, Permission.CODE_EXECUTE) is True

    # Member can execute code and conversations, but not user manage
    assert engine.has_permission(member, Permission.CONVERSATION_WRITE) is True
    assert engine.has_permission(member, Permission.CODE_EXECUTE) is True
    assert engine.has_permission(member, Permission.USER_MANAGE) is False
    with pytest.raises(AccessDeniedError):
        engine.assert_permission(member, Permission.USER_MANAGE)

    # Guest can only read and write conversations
    assert engine.has_permission(guest, Permission.CONVERSATION_READ) is True
    assert engine.has_permission(guest, Permission.CODE_EXECUTE) is False


# 2. Tests for SessionManager
def test_session_manager_lifecycle() -> None:
    sm = SessionManager(default_ttl_seconds=3600)
    user_id = "user-123"
    session, raw_token = sm.create_session(user_id, ip_address="127.0.0.1")

    assert session.user_id == user_id
    assert session.is_valid() is True

    # Authenticate session
    auth_session = sm.authenticate_session(raw_token)
    assert auth_session.session_id == session.session_id

    # Extend session
    extended = sm.extend_session(raw_token, additional_seconds=7200)
    assert extended.is_valid() is True

    # Revoke session
    sm.revoke_session(raw_token)
    with pytest.raises(SessionExpiredError):
        sm.authenticate_session(raw_token)


def test_session_manager_revoke_all_and_prune() -> None:
    sm = SessionManager(default_ttl_seconds=3600)
    user_id = "user-abc"
    _s1, _t1 = sm.create_session(user_id)
    _s2, _t2 = sm.create_session(user_id)

    assert len(sm.list_active_sessions(user_id)) == 2

    revoked_count = sm.revoke_all_user_sessions(user_id)
    assert revoked_count == 2
    assert len(sm.list_active_sessions(user_id)) == 0


# 3. Tests for DataOwnershipManager
def test_data_ownership_tenant_isolation() -> None:
    engine = AuthEngine()
    user_a = engine.register_user("usera", "a@test.com", "pwdA")
    user_b = engine.register_user("userb", "b@test.com", "pwdB")
    admin = engine.register_user("admin", "admin@test.com", "pwdAdmin", role=UserRole.ADMIN)

    dom = DataOwnershipManager(allow_admin_override=True)
    dom.register_resource("conversation", "conv-a-1", user_a.id)

    # User A accesses own resource
    assert dom.check_access(user_a, user_a.id) is True
    dom.assert_access(user_a, user_a.id, action="read")

    # User B cannot access User A's resource
    assert dom.check_access(user_b, user_a.id) is False
    with pytest.raises(AccessDeniedError):
        dom.assert_access(user_b, user_a.id, action="read")

    # Admin has override access
    assert dom.check_access(admin, user_a.id) is True
    dom.assert_access(admin, user_a.id, action="write")

    # Transfer ownership
    dom.transfer_ownership("conversation", "conv-a-1", user_b.id, requester=user_a)
    assert dom.get_owner("conversation", "conv-a-1") == user_b.id


# 4. Tests for QuotaManager
def test_quota_manager_rate_limits() -> None:
    qm = QuotaManager(
        custom_tier_limits={
            UserTier.FREE: QuotaLimits(requests_per_minute=3, tokens_per_day=1000, storage_bytes=1000)
        },
        rate_window_seconds=10.0,
    )
    user = User(username="test_rate", tier=UserTier.FREE)

    qm.record_request(user)
    qm.record_request(user)
    qm.record_request(user)

    with pytest.raises(RateLimitExceededError, match="Rate limit exceeded"):
        qm.record_request(user)


def test_quota_manager_tokens_and_storage() -> None:
    qm = QuotaManager(
        custom_tier_limits={
            UserTier.FREE: QuotaLimits(requests_per_minute=60, tokens_per_day=500, storage_bytes=1000)
        }
    )
    user = User(username="test_tokens", tier=UserTier.FREE)

    qm.check_and_record_tokens(user, 300)
    usage = qm.get_quota_usage(user)
    assert usage.tokens_used == 300

    # Exceeding tokens
    with pytest.raises(TokenQuotaExceededError, match="Daily token quota exceeded"):
        qm.check_and_record_tokens(user, 250)

    # Storage quota
    qm.record_storage(user, 800)
    usage = qm.get_quota_usage(user)
    assert usage.storage_used_bytes == 800

    with pytest.raises(StorageQuotaExceededError, match="Storage quota exceeded"):
        qm.record_storage(user, 300)


# 5. Tests for AccountLifecycleManager (GDPR Deletion & Audit Trail Boundary)
def test_account_lifecycle_deletion_and_anonymization(tmp_path: Path) -> None:
    app_config = AppConfig(storage_dir=tmp_path / "convs")
    app = ChadApp.create(app_config, DummyLapisClient())

    auth_engine = AuthEngine()
    session_manager = SessionManager()
    quota_manager = QuotaManager()
    dom = DataOwnershipManager()

    user = auth_engine.register_user("charlie", "charlie@chad.ai", "charlie123")
    _sess, _tok = session_manager.create_session(user.id)
    _key_rec, _raw_key = auth_engine.create_api_key(user.id)

    # Create owned conversation
    conv = Conversation(title="Charlie Conv", owner_id=user.id)
    app.store.save(conv)
    dom.register_resource("conversation", conv.id, user.id)

    lifecycle = AccountLifecycleManager(
        auth_engine=auth_engine,
        session_manager=session_manager,
        ownership_manager=dom,
        quota_manager=quota_manager,
        conversation_store=app.store,
    )

    # Anonymization check
    log_line = f"User charlie (id: {user.id}, email: charlie@chad.ai) performed sensitive tool execution"
    anonymized = lifecycle.anonymize_text(log_line, user)
    assert user.id not in anonymized
    assert "charlie@chad.ai" not in anonymized
    assert "[ANONYMIZED_USER:" in anonymized

    # Account cascade deletion
    report = lifecycle.delete_account(user.id, cascade=True)
    assert report["sessions_revoked"] == 1
    assert report["conversations_deleted"] == 1

    # Verify user is gone from auth engine
    with pytest.raises(UserNotFoundError):
        auth_engine.get_user(user.id)

    # Verify conversation is gone from store
    with pytest.raises(KeyError):
        app.store.load(conv.id)


# 6. Web API integration tests for multi-user platform
def test_web_api_multi_user_flow(tmp_path: Path) -> None:
    app_config = AppConfig(storage_dir=tmp_path / "web_storage")
    app = ChadApp.create(app_config, DummyLapisClient())

    auth_engine = AuthEngine()
    session_manager = SessionManager()
    quota_manager = QuotaManager(
        custom_tier_limits={
            UserTier.FREE: QuotaLimits(requests_per_minute=2, tokens_per_day=1000)
        }
    )
    dom = DataOwnershipManager()
    lifecycle = AccountLifecycleManager(
        auth_engine=auth_engine,
        session_manager=session_manager,
        ownership_manager=dom,
        quota_manager=quota_manager,
        conversation_store=app.store,
    )

    server = create_web_server(
        app=app,
        host="127.0.0.1",
        port=0,
        auth_engine=auth_engine,
        session_manager=session_manager,
        quota_manager=quota_manager,
        ownership_manager=dom,
        lifecycle_manager=lifecycle,
    )
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()

    try:
        base_url = f"http://{host}:{port}"

        # 1. Register User 1
        status, body = _http_request(
            f"{base_url}/api/auth/register",
            method="POST",
            data={
                "username": "user1",
                "email": "user1@example.com",
                "password": "Password123!",
                "role": "member",
                "tier": "free",
            },
        )
        assert status == 201
        user1_id = body["user"]["id"]

        # 2. Login User 1
        status, body = _http_request(
            f"{base_url}/api/auth/login",
            method="POST",
            data={"username": "user1", "password": "Password123!"},
        )
        assert status == 200
        token1 = body["token"]
        auth1_headers = {"Authorization": f"Bearer {token1}"}

        # 3. GET /api/auth/me
        status, body = _http_request(
            f"{base_url}/api/auth/me",
            headers=auth1_headers,
        )
        assert status == 200
        assert body["user"]["id"] == user1_id

        # 4. Create conversation as User 1
        status, body = _http_request(
            f"{base_url}/api/conversations",
            method="POST",
            headers=auth1_headers,
        )
        assert status == 201
        conv1_id = body["conversation"]["id"]
        assert body["conversation"]["owner_id"] == user1_id

        # 5. Register & login User 2
        status, body = _http_request(
            f"{base_url}/api/auth/register",
            method="POST",
            data={
                "username": "user2",
                "email": "user2@example.com",
                "password": "Password456!",
                "role": "member",
                "tier": "free",
            },
        )
        assert status == 201
        status, body = _http_request(
            f"{base_url}/api/auth/login",
            method="POST",
            data={"username": "user2", "password": "Password456!"},
        )
        token2 = body["token"]
        auth2_headers = {"Authorization": f"Bearer {token2}"}

        # 6. User 2 tries to read User 1's conversation -> FORBIDDEN 403
        status, body = _http_request(
            f"{base_url}/api/conversations/{conv1_id}",
            headers=auth2_headers,
        )
        assert status == 403

        # 7. Quota enforcement on /api/chat (limit is 2 req/min)
        status, _ = _http_request(
            f"{base_url}/api/chat",
            method="POST",
            data={"text": "message 1"},
            headers=auth1_headers,
        )
        assert status == 200

        status, _ = _http_request(
            f"{base_url}/api/chat",
            method="POST",
            data={"text": "message 2"},
            headers=auth1_headers,
        )
        assert status == 200

        # 3rd request hits rate limit -> 429
        status, body = _http_request(
            f"{base_url}/api/chat",
            method="POST",
            data={"text": "message 3"},
            headers=auth1_headers,
        )
        assert status == 429
        assert "Rate limit exceeded" in body["error"]

        # 8. Check quota status endpoint
        status, body = _http_request(
            f"{base_url}/api/auth/quota",
            headers=auth1_headers,
        )
        assert status == 200
        assert body["quota"]["requests_count"] >= 2

        # 9. Delete account
        status, body = _http_request(
            f"{base_url}/api/auth/account",
            method="DELETE",
            headers=auth1_headers,
        )
        assert status == 200
        assert body["status"] == "deleted"

    finally:
        server.shutdown()
        server.server_close()
