from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from chad.auth.models import AccessDeniedError, User, UserRole


@dataclass(slots=True)
class ResourceRecord:
    id: str = field(default_factory=lambda: str(uuid4()))
    resource_type: str = "conversation"
    resource_id: str = ""
    owner_id: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


class DataOwnershipManager:
    """Enforces strict tenant isolation and data ownership across users."""

    def __init__(self, allow_admin_override: bool = True) -> None:
        self.allow_admin_override = allow_admin_override
        self._resources: dict[tuple[str, str], ResourceRecord] = {}  # (type, resource_id) -> record

    def register_resource(
        self,
        resource_type: str,
        resource_id: str,
        owner_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> ResourceRecord:
        record = ResourceRecord(
            resource_type=resource_type,
            resource_id=resource_id,
            owner_id=owner_id,
            metadata=metadata or {},
        )
        self._resources[(resource_type, resource_id)] = record
        return record

    def unregister_resource(self, resource_type: str, resource_id: str) -> None:
        self._resources.pop((resource_type, resource_id), None)

    def get_owner(self, resource_type: str, resource_id: str) -> str | None:
        record = self._resources.get((resource_type, resource_id))
        return record.owner_id if record else None

    def check_access(
        self,
        user: User,
        owner_id: str | None,
        action: str = "read",
    ) -> bool:
        if not user.is_active:
            return False

        # If resource has no owner specified, it's considered unassigned/system
        if owner_id is None:
            return True

        # Owner always has access
        if owner_id == user.id:
            return True

        # Admin override
        return bool(self.allow_admin_override and user.role == UserRole.ADMIN)

    def assert_access(
        self,
        user: User,
        owner_id: str | None,
        action: str = "read",
        resource_info: str | None = None,
    ) -> None:
        if not self.check_access(user, owner_id, action=action):
            target = f" on {resource_info}" if resource_info else ""
            raise AccessDeniedError(
                f"User '{user.username}' (id: {user.id}) is not authorized for '{action}' action{target} owned by '{owner_id}'."
            )

    def transfer_ownership(
        self,
        resource_type: str,
        resource_id: str,
        new_owner_id: str,
        requester: User,
    ) -> ResourceRecord:
        key = (resource_type, resource_id)
        record = self._resources.get(key)
        if record is None:
            # If not tracked yet, register under new owner if requester has permissions
            if requester.role != UserRole.ADMIN:
                raise AccessDeniedError("Only admin can register untracked resource transfer")
            return self.register_resource(resource_type, resource_id, new_owner_id)

        self.assert_access(requester, record.owner_id, action="transfer")
        record.owner_id = new_owner_id
        return record
