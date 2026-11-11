from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from chad.projects.models import Project, ProjectMember, ProjectRole


class ProjectAccessError(Exception):
    """Raised when access to a project or project action is forbidden."""


class ProjectNotFoundError(Exception):
    """Raised when a requested project is not found."""


class ProjectManager:
    """Manages project workspaces, memberships, associated resources, and file isolation."""

    def __init__(self, base_storage_dir: str | Path | None = None) -> None:
        self.base_storage_dir = Path(base_storage_dir) if base_storage_dir else None
        self._projects: dict[str, Project] = {}
        if self.base_storage_dir:
            self.base_storage_dir.mkdir(parents=True, exist_ok=True)
            self._load_all()

    def _project_file(self, project_id: str) -> Path | None:
        if not self.base_storage_dir:
            return None
        return self.base_storage_dir / f"{project_id}.json"

    def _workspace_dir(self, project_id: str) -> Path | None:
        if not self.base_storage_dir:
            return None
        ws_dir = self.base_storage_dir / "workspaces" / project_id
        ws_dir.mkdir(parents=True, exist_ok=True)
        return ws_dir

    def create_project(
        self,
        name: str,
        owner_id: str,
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Project:
        if not name.strip():
            raise ValueError("Project name cannot be empty.")
        if not owner_id.strip():
            raise ValueError("Project owner_id cannot be empty.")

        project = Project(
            name=name.strip(),
            owner_id=owner_id,
            description=description.strip(),
            metadata=metadata or {},
        )
        self._projects[project.project_id] = project
        self._save(project)
        # Initialize workspace directory
        if self.base_storage_dir:
            self._workspace_dir(project.project_id)
        return project

    def get_project(self, project_id: str) -> Project:
        project = self._projects.get(project_id)
        if not project:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")
        return project

    def list_projects(self, user_id: str | None = None) -> list[Project]:
        projects = list(self._projects.values())
        if user_id is not None:
            projects = [p for p in projects if user_id in p.members]
        return sorted(projects, key=lambda p: p.created_at, reverse=True)

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> Project:
        project = self.get_project(project_id)
        if name is not None:
            if not name.strip():
                raise ValueError("Project name cannot be empty.")
            project.name = name.strip()
        if description is not None:
            project.description = description.strip()
        if metadata is not None:
            project.metadata.update(metadata)

        project.updated_at = datetime.now(UTC).isoformat()
        self._save(project)
        return project

    def delete_project(self, project_id: str) -> None:
        if project_id not in self._projects:
            raise ProjectNotFoundError(f"Project '{project_id}' not found.")
        del self._projects[project_id]

        if self.base_storage_dir:
            p_file = self._project_file(project_id)
            if p_file and p_file.exists():
                p_file.unlink()

    def add_member(
        self,
        project_id: str,
        user_id: str,
        role: ProjectRole = ProjectRole.VIEWER,
    ) -> ProjectMember:
        project = self.get_project(project_id)
        member = ProjectMember(user_id=user_id, role=role)
        project.members[user_id] = member
        project.updated_at = datetime.now(UTC).isoformat()
        self._save(project)
        return member

    def remove_member(self, project_id: str, user_id: str) -> None:
        project = self.get_project(project_id)
        if user_id == project.owner_id:
            raise ValueError("Cannot remove the project owner from project members.")
        if user_id in project.members:
            del project.members[user_id]
            project.updated_at = datetime.now(UTC).isoformat()
            self._save(project)

    def can_access(self, user_id: str, project_id: str, action: str = "read") -> bool:
        try:
            project = self.get_project(project_id)
        except ProjectNotFoundError:
            return False

        member = project.members.get(user_id)
        if not member:
            return False

        if member.role == ProjectRole.OWNER:
            return True
        if member.role == ProjectRole.EDITOR:
            return action in ("read", "write", "execute", "link")
        if member.role == ProjectRole.VIEWER:
            return action == "read"
        return False

    def require_access(self, user_id: str, project_id: str, action: str = "read") -> None:
        if not self.can_access(user_id, project_id, action):
            raise ProjectAccessError(
                f"User '{user_id}' does not have '{action}' permission for project '{project_id}'."
            )

    def link_conversation(self, project_id: str, conversation_id: str) -> None:
        project = self.get_project(project_id)
        if conversation_id not in project.conversation_ids:
            project.conversation_ids.append(conversation_id)
            project.updated_at = datetime.now(UTC).isoformat()
            self._save(project)

    def unlink_conversation(self, project_id: str, conversation_id: str) -> None:
        project = self.get_project(project_id)
        if conversation_id in project.conversation_ids:
            project.conversation_ids.remove(conversation_id)
            project.updated_at = datetime.now(UTC).isoformat()
            self._save(project)

    def link_file(self, project_id: str, file_id: str) -> None:
        project = self.get_project(project_id)
        if file_id not in project.file_ids:
            project.file_ids.append(file_id)
            project.updated_at = datetime.now(UTC).isoformat()
            self._save(project)

    def unlink_file(self, project_id: str, file_id: str) -> None:
        project = self.get_project(project_id)
        if file_id in project.file_ids:
            project.file_ids.remove(file_id)
            project.updated_at = datetime.now(UTC).isoformat()
            self._save(project)

    # Workspace file isolation methods
    def resolve_workspace_path(self, project_id: str, relative_path: str) -> Path:
        """Resolves relative file path safely inside the project workspace directory."""
        if not self.base_storage_dir:
            raise ValueError("No base storage directory configured for workspace isolation.")
        self.get_project(project_id)  # verify project exists
        ws_dir = self._workspace_dir(project_id)
        assert ws_dir is not None

        resolved = (ws_dir / relative_path).resolve()
        try:
            resolved.relative_to(ws_dir.resolve())
        except ValueError as err:
            raise ValueError(
                f"Path traversal detected: '{relative_path}' is outside project workspace '{ws_dir}'."
            ) from err
        return resolved

    def write_workspace_file(self, project_id: str, relative_path: str, content: str | bytes) -> Path:
        target = self.resolve_workspace_path(project_id, relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, str):
            target.write_text(content, encoding="utf-8")
        else:
            target.write_bytes(content)
        return target

    def read_workspace_file(self, project_id: str, relative_path: str) -> str:
        target = self.resolve_workspace_path(project_id, relative_path)
        if not target.exists():
            raise FileNotFoundError(f"File '{relative_path}' not found in project workspace.")
        return target.read_text(encoding="utf-8")

    def list_workspace_files(self, project_id: str) -> list[str]:
        if not self.base_storage_dir:
            return []
        self.get_project(project_id)
        ws_dir = self._workspace_dir(project_id)
        assert ws_dir is not None

        files: list[str] = []
        for path in ws_dir.rglob("*"):
            if path.is_file():
                rel = path.relative_to(ws_dir).as_posix()
                files.append(rel)
        return sorted(files)

    def _save(self, project: Project) -> None:
        p_file = self._project_file(project.project_id)
        if not p_file:
            return
        p_file.parent.mkdir(parents=True, exist_ok=True)
        p_file.write_text(json.dumps(project.to_dict(), indent=2), encoding="utf-8")

    def _load_all(self) -> None:
        if not self.base_storage_dir or not self.base_storage_dir.exists():
            return
        for file in self.base_storage_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if "project_id" in data and "owner_id" in data:
                    project = Project.from_dict(data)
                    self._projects[project.project_id] = project
            except (json.JSONDecodeError, KeyError):
                continue
