from __future__ import annotations

from datetime import UTC, datetime, timedelta

from chad.auth.models import Session, User
from chad.auth.security import generate_session_token


class SessionManager:
    """Manages multi-user authentication sessions and token validation."""

    def __init__(self, default_ttl_seconds: int = 86400) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._sessions: dict[str, Session] = {}  # token -> Session
        self._user_sessions: dict[str, set[str]] = {}  # user_id -> set of tokens

    def create_session(self, user: User, ttl_seconds: int | None = None) -> Session:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        expires = datetime.now(UTC) + timedelta(seconds=ttl)
        token = generate_session_token()
        session = Session(
            token=token,
            user_id=user.id,
            expires_at=expires.isoformat(),
        )
        self._sessions[token] = session
        if user.id not in self._user_sessions:
            self._user_sessions[user.id] = set()
        self._user_sessions[user.id].add(token)
        return session

    def get_session(self, token: str) -> Session | None:
        session = self._sessions.get(token)
        if not session:
            return None
        if not session.is_valid():
            return None
        return session

    def validate_token(self, token: str) -> str | None:
        """Returns user_id if valid, else None."""
        session = self.get_session(token)
        if session:
            return session.user_id
        return None

    def revoke_session(self, token: str) -> bool:
        session = self._sessions.get(token)
        if not session:
            return False
        session.is_revoked = True
        return True

    def revoke_all_for_user(self, user_id: str) -> int:
        tokens = self._user_sessions.get(user_id, set())
        revoked_count = 0
        for token in tokens:
            session = self._sessions.get(token)
            if session and not session.is_revoked:
                session.is_revoked = True
                revoked_count += 1
        return revoked_count

    def purge_expired(self) -> int:
        expired_tokens = [
            t for t, s in self._sessions.items()
            if not s.is_valid()
        ]
        for t in expired_tokens:
            s = self._sessions.pop(t, None)
            if s and s.user_id in self._user_sessions:
                self._user_sessions[s.user_id].discard(t)
        return len(expired_tokens)
