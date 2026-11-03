from __future__ import annotations

import hashlib
from typing import Any

from chad.auth.engine import AuthEngine
from chad.auth.models import User
from chad.auth.ownership import DataOwnershipManager
from chad.auth.quotas import QuotaManager
from chad.auth.sessions import SessionManager
from chad.memory.store import MemoryStore
from chad.storage.json_store import ConversationStore


class AccountLifecycleManager:
    """Orchestrates account deletion, cascade data purging, and audit anonymization."""

    def __init__(
        self,
        auth_engine: AuthEngine,
        session_manager: SessionManager | None = None,
        ownership_manager: DataOwnershipManager | None = None,
        quota_manager: QuotaManager | None = None,
        conversation_store: ConversationStore | None = None,
        memory_store: MemoryStore | None = None,
    ) -> None:
        self.auth_engine = auth_engine
        self.session_manager = session_manager
        self.ownership_manager = ownership_manager
        self.quota_manager = quota_manager
        self.conversation_store = conversation_store
        self.memory_store = memory_store

    @staticmethod
    def get_pseudonym(user_id: str) -> str:
        digest = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12]
        return f"[ANONYMIZED_USER:{digest}]"

    def anonymize_text(self, text: str, user: User) -> str:
        pseudonym = self.get_pseudonym(user.id)
        sanitized = text.replace(user.id, pseudonym)
        if user.username:
            sanitized = sanitized.replace(user.username, pseudonym)
        if user.email:
            sanitized = sanitized.replace(user.email, pseudonym)
        return sanitized

    def delete_account(
        self,
        user_id: str,
        cascade: bool = True,
    ) -> dict[str, Any]:
        user = self.auth_engine.get_user(user_id)
        report: dict[str, Any] = {
            "user_id": user_id,
            "pseudonym": self.get_pseudonym(user_id),
            "sessions_revoked": 0,
            "conversations_deleted": 0,
            "memories_deleted": 0,
            "quotas_reset": False,
        }

        # 1. Revoke sessions
        if self.session_manager is not None:
            revoked = self.session_manager.revoke_all_user_sessions(user_id)
            report["sessions_revoked"] = revoked

        # 2. Reset quotas
        if self.quota_manager is not None:
            self.quota_manager.reset_user(user_id)
            report["quotas_reset"] = True

        # 3. Cascade delete owned conversations
        if cascade and self.conversation_store is not None:
            user_convs = self.conversation_store.list(include_archived=True, include_deleted=True)
            for conv in user_convs:
                if getattr(conv, "owner_id", None) == user_id:
                    try:
                        self.conversation_store.delete(conv.id, hard=True)
                        report["conversations_deleted"] += 1
                    except (KeyError, OSError):
                        continue

        # 4. Cascade delete memory items
        if cascade and self.memory_store is not None:
            all_memories = self.memory_store.list()
            for mem in all_memories:
                if getattr(mem, "user_id", None) == user_id:
                    try:
                        self.memory_store.delete(mem.id)
                        report["memories_deleted"] += 1
                    except (KeyError, OSError):
                        continue

        # 5. Revoke any API keys
        for _key_id, record in list(self.auth_engine._api_keys.items()):
            if record.user_id == user_id:
                record.is_revoked = True

        # 6. Remove user from auth engine
        self.auth_engine._users.pop(user_id, None)
        u_norm = user.username.strip().lower()
        e_norm = user.email.strip().lower()
        self.auth_engine._username_index.pop(u_norm, None)
        self.auth_engine._email_index.pop(e_norm, None)

        return report
