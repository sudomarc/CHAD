from __future__ import annotations

import json
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from chad.app import ChadApp
from chad.auth import (
    AccessDeniedError,
    AccountLifecycleManager,
    DataOwnershipManager,
    Permission,
    QuotaExceededError,
    QuotaManager,
    SessionManager,
    User,
    UserQuota,
    UserRole,
    generate_salt,
    hash_password,
    verify_password,
)
from chad.core.config import AppConfig
from chad.core.conversation import ChatRequest
from chad.interfaces.web import create_web_server
from chad.llm.client import LapisClient, ModelInfo


class MockLapisClient(LapisClient):
    def generate(self, request: ChatRequest) -> str:
        last_msg = request.messages[-1].content
        return f"Echo: {last_msg}"

    def current_model(self) -> ModelInfo:
        return ModelInfo(id="test-model", display_name="Test Model")


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


def test_password_security():
    salt = generate_salt()
    pwd = "super-secret-password"
    hashed = hash_password(pwd, salt)

    assert verify_password(pwd, salt, hashed) is True
    assert verify_password("wrong-password", salt, hashed) is False
    assert len(salt) == 32  # 16 bytes hex
    assert len(hashed) == 64  # sha256 hex


def test_user_roles_and_permissions():
    admin = User(id="u1", username="admin", password_hash="", salt="", role=UserRole.ADMIN)
    member = User(id="u2", username="member", password_hash="", salt="", role=UserRole.MEMBER)
    guest = User(id="u3", username="guest", password_hash="", salt="", role=UserRole.GUEST)

    assert admin.has_permission(Permission.USER_MANAGE) is True
    assert admin.has_permission(Permission.SYSTEM_CONFIG) is True
    assert admin.has_permission(Permission.CONVERSATION_CREATE) is True

    assert member.has_permission(Permission.USER_MANAGE) is False
    assert member.has_permission(Permission.CONVERSATION_CREATE) is True
    assert member.has_permission(Permission.TOOL_USE) is True

    assert guest.has_permission(Permission.CONVERSATION_SHARE) is False
    assert guest.has_permission(Permission.MEMORY_WRITE) is False
    assert guest.has_permission(Permission.CONVERSATION_CREATE) is True


def test_session_lifecycle():
    mgr = SessionManager(default_ttl_seconds=2)
    user = User(id="u1", username="alice", password_hash="", salt="")

    session = mgr.create_session(user)
    assert session.is_valid() is True
    assert mgr.validate_token(session.token) == "u1"

    # Revocation
    mgr.revoke_session(session.token)
    assert session.is_valid() is False
    assert mgr.validate_token(session.token) is None

    # Expiry
    session2 = mgr.create_session(user, ttl_seconds=1)
    time.sleep(1.1)
    assert session2.is_valid() is False
    assert mgr.validate_token(session2.token) is None

    # Purge expired
    purged = mgr.purge_expired()
    assert purged >= 1


def test_data_ownership_and_isolation():
    mgr = DataOwnershipManager()
    alice = User(id="u1", username="alice", password_hash="", salt="", role=UserRole.MEMBER)
    bob = User(id="u2", username="bob", password_hash="", salt="", role=UserRole.MEMBER)
    admin = User(id="u3", username="admin", password_hash="", salt="", role=UserRole.ADMIN)

    conv_id = "conv-100"
    mgr.assign_owner(conv_id, alice.id)

    # Alice can read/write/delete
    assert mgr.can_access(alice, conv_id, "read") is True
    assert mgr.can_access(alice, conv_id, "delete") is True

    # Bob cannot access
    assert mgr.can_access(bob, conv_id, "read") is False
    with pytest.raises(AccessDeniedError):
        mgr.require_access(bob, conv_id, "read")

    # Admin can access anything
    assert mgr.can_access(admin, conv_id, "read") is True
    assert mgr.can_access(admin, conv_id, "delete") is True

    # Alice shares with Bob
    mgr.share_resource(conv_id, alice, bob.id)
    assert mgr.can_access(bob, conv_id, "read") is True
    assert mgr.can_access(bob, conv_id, "write") is True
    # Bob still cannot delete
    assert mgr.can_access(bob, conv_id, "delete") is False


def test_quotas_and_rate_limits():
    q_mgr = QuotaManager()
    quotas = UserQuota(requests_per_minute=2, max_tokens_per_day=1000, max_storage_bytes=100)
    user = User(id="u1", username="alice", password_hash="", salt="", quotas=quotas)

    # Rate limiting
    assert q_mgr.check_rate_limit(user) is True
    assert q_mgr.check_rate_limit(user) is True
    assert q_mgr.check_rate_limit(user) is False
    with pytest.raises(QuotaExceededError):
        q_mgr.require_rate_limit(user)

    # Token quotas
    assert q_mgr.check_token_quota(user, 500) is True
    q_mgr.record_tokens(user, 500)
    assert user.quotas.used_tokens_today == 500

    assert q_mgr.check_token_quota(user, 600) is False
    with pytest.raises(QuotaExceededError):
        q_mgr.record_tokens(user, 600)

    # Storage quotas
    assert q_mgr.check_storage_quota(user, 50) is True
    q_mgr.record_storage(user, 50)
    assert user.quotas.used_storage_bytes == 50

    q_mgr.release_storage(user, 30)
    assert user.quotas.used_storage_bytes == 20

    with pytest.raises(QuotaExceededError):
        q_mgr.record_storage(user, 100)


def test_account_deletion_and_gdpr_anonymization():
    s_mgr = SessionManager()
    own_mgr = DataOwnershipManager()
    user = User(id="usr_xyz", username="dave", password_hash="", salt="")
    user_store = {user.id: user}

    s_mgr.create_session(user)
    own_mgr.assign_owner("conv_1", user.id)
    own_mgr.assign_owner("conv_2", user.id)

    lifecycle = AccountLifecycleManager(s_mgr, own_mgr, user_store)

    audit_trail = [
        {"id": "ev_1", "user_id": "usr_xyz", "action": "login"},
        {"id": "ev_2", "user_id": "other_user", "action": "login"},
    ]

    res = lifecycle.delete_account("usr_xyz", audit_trail)
    assert res["deleted_user_id"] == "usr_xyz"
    assert res["pseudonym"].startswith("anon_")
    assert res["revoked_sessions"] == 1
    assert len(res["cleaned_resources"]) == 2
    assert "usr_xyz" not in user_store

    # Verify audit boundary
    assert audit_trail[0]["user_id"] == res["pseudonym"]
    assert audit_trail[0]["anonymized"] is True
    assert audit_trail[1]["user_id"] == "other_user"


def test_web_auth_endpoints(tmp_path: Path):
    config = AppConfig(storage_dir=tmp_path / "storage")
    client = MockLapisClient()
    app = ChadApp.create(config, client)

    server = create_web_server(app, host="127.0.0.1", port=0)
    host, port = server.server_address
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://{host}:{port}"

    try:
        # 1. Register user
        reg_status, reg_data = _http_request(
            f"{base_url}/api/auth/register",
            method="POST",
            data={"username": "alice", "password": "secretpassword", "email": "alice@example.com"},
        )
        assert reg_status == 201
        assert "token" in reg_data
        assert reg_data["user"]["username"] == "alice"
        token = reg_data["token"]

        # Duplicate registration fails
        dup_status, dup_data = _http_request(
            f"{base_url}/api/auth/register",
            method="POST",
            data={"username": "alice", "password": "anotherpassword"},
        )
        assert dup_status == 409
        assert "error" in dup_data

        # 2. Login
        login_status, login_data = _http_request(
            f"{base_url}/api/auth/login",
            method="POST",
            data={"username": "alice", "password": "secretpassword"},
        )
        assert login_status == 200
        assert "token" in login_data
        token = login_data["token"]

        # 3. GET /api/auth/me
        me_status, me_data = _http_request(
            f"{base_url}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_status == 200
        assert me_data["user"]["username"] == "alice"

        # 4. GET /api/auth/quota
        q_status, q_data = _http_request(
            f"{base_url}/api/auth/quota",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert q_status == 200
        assert "max_tokens_per_day" in q_data["quotas"]

        # 5. Create conversation as Alice
        conv_status, conv_data = _http_request(
            f"{base_url}/api/conversations",
            method="POST",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert conv_status == 201
        assert "conversation" in conv_data

        # 6. Delete account
        del_status, del_data = _http_request(
            f"{base_url}/api/auth/account",
            method="DELETE",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert del_status == 200
        assert del_data["status"] == "deleted"

        # After deletion, token is revoked
        me_after_status, _ = _http_request(
            f"{base_url}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_after_status == 401

    finally:
        server.shutdown()
        server.server_close()
