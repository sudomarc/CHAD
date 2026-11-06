from __future__ import annotations

from chad.auth.models import Permission, User, UserRole


class AccessDeniedError(Exception):
    """Raised when an operation violates data ownership or authorization policy."""


class DataOwnershipManager:
    """Enforces multi-tenant data ownership and resource access validation."""

    def __init__(self) -> None:
        # resource_id -> owner_user_id
        self._resource_owners: dict[str, str] = {}
        # resource_id -> set of shared user_ids (read/write access)
        self._resource_collaborators: dict[str, set[str]] = {}

    def assign_owner(self, resource_id: str, user_id: str) -> None:
        self._resource_owners[resource_id] = user_id

    def get_owner(self, resource_id: str) -> str | None:
        return self._resource_owners.get(resource_id)

    def share_resource(self, resource_id: str, owner: User, target_user_id: str) -> None:
        if not owner.has_permission(Permission.CONVERSATION_SHARE):
            raise AccessDeniedError(f"User {owner.id} lacks permission to share resources")
        actual_owner = self.get_owner(resource_id)
        if actual_owner and actual_owner != owner.id and owner.role != UserRole.ADMIN:
            raise AccessDeniedError("Only the resource owner or an admin may share it")

        if resource_id not in self._resource_collaborators:
            self._resource_collaborators[resource_id] = set()
        self._resource_collaborators[resource_id].add(target_user_id)

    def can_access(self, user: User, resource_id: str, action: str = "read") -> bool:
        """Determines if a user has access to a specific resource."""
        # Admins have global access
        if user.role == UserRole.ADMIN:
            return True

        owner_id = self.get_owner(resource_id)
        # If unowned (legacy or global), accessible by authenticated user
        if owner_id is None:
            return True

        if owner_id == user.id:
            return True

        # Check collaborator access
        collaborators = self._resource_collaborators.get(resource_id, set())
        return user.id in collaborators and action in ("read", "write")

    def require_access(self, user: User, resource_id: str, action: str = "read") -> None:
        if not self.can_access(user, resource_id, action):
            raise AccessDeniedError(
                f"User {user.id} ({user.username}) cannot perform '{action}' on resource {resource_id}"
            )

    def remove_resource(self, resource_id: str) -> None:
        self._resource_owners.pop(resource_id, None)
        self._resource_collaborators.pop(resource_id, None)

    def list_user_resources(self, user_id: str) -> list[str]:
        return [res_id for res_id, uid in self._resource_owners.items() if uid == user_id]
