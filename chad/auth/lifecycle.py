from __future__ import annotations

import hashlib
from typing import Any

from chad.auth.models import User
from chad.auth.ownership import DataOwnershipManager
from chad.auth.session import SessionManager


class AccountLifecycleManager:
    """Handles GDPR account deletion, cascaded resource cleanup, and audit trail boundary anonymization."""

    def __init__(
        self,
        session_manager: SessionManager,
        ownership_manager: DataOwnershipManager,
        user_store: dict[str, User] | None = None,
    ) -> None:
        self.session_manager = session_manager
        self.ownership_manager = ownership_manager
        self.user_store = user_store if user_store is not None else {}
        self._anonymized_audit_logs: list[dict[str, Any]] = []

    def anonymize_identity(self, user_id: str) -> str:
        """Derives a pseudonymous, one-way hash token for audit preservation under GDPR."""
        return f"anon_{hashlib.sha256(user_id.encode('utf-8')).hexdigest()[:12]}"

    def delete_account(
        self,
        user_id: str,
        audit_trail: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Performs complete user account deletion:

        1. Revokes all active sessions.
        2. Cleans up owned resources / isolation tags.
        3. Removes user record from identity store.
        4. Replaces user identifiers in audit trails with an irreversible anonymized ID.
        """
        user = self.user_store.get(user_id)
        if not user:
            raise KeyError(f"User {user_id} not found")

        # 1. Revoke all active sessions
        revoked_sessions = self.session_manager.revoke_all_for_user(user_id)

        # 2. Collect and clean up owned resources
        owned_resources = self.ownership_manager.list_user_resources(user_id)
        for res_id in owned_resources:
            self.ownership_manager.remove_resource(res_id)

        # 3. Anonymize audit boundary
        pseudonym = self.anonymize_identity(user_id)
        anonymized_count = 0
        if audit_trail:
            for entry in audit_trail:
                if entry.get("user_id") == user_id:
                    entry["user_id"] = pseudonym
                    entry["anonymized"] = True
                    anonymized_count += 1
                    self._anonymized_audit_logs.append(entry)

        # 4. Remove user record completely
        del self.user_store[user_id]

        return {
            "deleted_user_id": user_id,
            "pseudonym": pseudonym,
            "revoked_sessions": revoked_sessions,
            "cleaned_resources": owned_resources,
            "anonymized_audit_entries": anonymized_count,
        }
