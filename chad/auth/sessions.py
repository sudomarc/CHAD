from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from chad.auth.models import InvalidCredentialsError, SessionExpiredError, SessionRecord


class SessionManager:
    """Manages active user sessions, token lifecycles, and revocation."""

    def __init__(self, default_ttl_seconds: int = 86400 * 7) -> None:  # default 7 days
        self.default_ttl_seconds = default_ttl_seconds
        self._sessions: dict[str, SessionRecord] = {}  # session_id -> SessionRecord
        self._token_hash_index: dict[str, str] = {}  # token_hash -> session_id

    @staticmethod
    def _hash_token(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def create_session(
        self,
        user_id: str,
        ttl_seconds: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> tuple[SessionRecord, str]:
        raw_token = secrets.token_urlsafe(32)
        token_hash = self._hash_token(raw_token)

        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires_at = (datetime.now(UTC) + timedelta(seconds=ttl)).isoformat()

        session = SessionRecord(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self._sessions[session.session_id] = session
        self._token_hash_index[token_hash] = session.session_id
        return session, raw_token

    def authenticate_session(self, raw_token: str) -> SessionRecord:
        token_hash = self._hash_token(raw_token)
        session_id = self._token_hash_index.get(token_hash)
        if session_id is None:
            raise InvalidCredentialsError("Invalid session token")

        session = self._sessions[session_id]
        if not session.is_valid():
            raise SessionExpiredError("Session has expired or been revoked")

        # Update last_active_at
        session.last_active_at = datetime.now(UTC).isoformat()
        return session

    def extend_session(self, raw_token: str, additional_seconds: int | None = None) -> SessionRecord:
        session = self.authenticate_session(raw_token)
        ttl = additional_seconds if additional_seconds is not None else self.default_ttl_seconds
        session.expires_at = (datetime.now(UTC) + timedelta(seconds=ttl)).isoformat()
        return session

    def revoke_session(self, raw_token: str) -> None:
        token_hash = self._hash_token(raw_token)
        session_id = self._token_hash_index.get(token_hash)
        if session_id and session_id in self._sessions:
            self._sessions[session_id].is_revoked = True

    def revoke_all_user_sessions(self, user_id: str) -> int:
        revoked_count = 0
        for session in self._sessions.values():
            if session.user_id == user_id and not session.is_revoked:
                session.is_revoked = True
                revoked_count += 1
        return revoked_count

    def list_active_sessions(self, user_id: str) -> list[SessionRecord]:
        now = datetime.now(UTC)
        return [
            s for s in self._sessions.values()
            if s.user_id == user_id and s.is_valid(now)
        ]

    def prune_expired(self) -> int:
        now = datetime.now(UTC)
        expired_ids = [
            sid for sid, s in self._sessions.items()
            if not s.is_valid(now)
        ]
        for sid in expired_ids:
            sess = self._sessions.pop(sid)
            self._token_hash_index.pop(sess.token_hash, None)
        return len(expired_ids)
