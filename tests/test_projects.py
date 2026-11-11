from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from chad.projects.manager import (
    ProjectAccessError,
    ProjectManager,
    ProjectNotFoundError,
)
from chad.projects.models import Project, ProjectRole


@pytest.fixture
def temp_project_dir():
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


def test_project_model_serialization():
    p = Project(
        name="Research Assistant",
        owner_id="user_123",
        description="A research agent workspace",
        metadata={"tags": ["ai", "research"]},
    )
    assert p.project_id is not None
    assert "user_123" in p.members
    assert p.members["user_123"].role == ProjectRole.OWNER

    p_dict = p.to_dict()
    assert p_dict["name"] == "Research Assistant"
    assert p_dict["owner_id"] == "user_123"
    assert p_dict["members"]["user_123"]["role"] == "owner"

    restored = Project.from_dict(p_dict)
    assert restored.project_id == p.project_id
    assert restored.name == p.name
    assert restored.owner_id == p.owner_id
    assert restored.members["user_123"].role == ProjectRole.OWNER


def test_project_manager_crud(temp_project_dir):
    mgr = ProjectManager(base_storage_dir=temp_project_dir)

    # Create project
    proj = mgr.create_project(
        name="CHAD Core",
        owner_id="admin_1",
        description="Agent runtime repo",
        metadata={"priority": 1},
    )
    assert proj.project_id is not None
    assert proj.name == "CHAD Core"

    # Get project
    loaded = mgr.get_project(proj.project_id)
    assert loaded.name == "CHAD Core"
    assert loaded.owner_id == "admin_1"

    # Update project
    updated = mgr.update_project(
        proj.project_id,
        name="CHAD Core v2",
        description="Updated description",
        metadata={"version": "2.0"},
    )
    assert updated.name == "CHAD Core v2"
    assert updated.description == "Updated description"
    assert updated.metadata["version"] == "2.0"

    # List projects
    all_proj = mgr.list_projects()
    assert len(all_proj) == 1
    assert all_proj[0].project_id == proj.project_id

    # Filter list by user_id
    assert len(mgr.list_projects(user_id="admin_1")) == 1
    assert len(mgr.list_projects(user_id="other_user")) == 0

    # Delete project
    mgr.delete_project(proj.project_id)
    with pytest.raises(ProjectNotFoundError):
        mgr.get_project(proj.project_id)


def test_project_manager_persistence(temp_project_dir):
    mgr1 = ProjectManager(base_storage_dir=temp_project_dir)
    p = mgr1.create_project(name="Persistent Proj", owner_id="user_pers")
    pid = p.project_id

    # Reload in fresh manager instance
    mgr2 = ProjectManager(base_storage_dir=temp_project_dir)
    loaded = mgr2.get_project(pid)
    assert loaded.name == "Persistent Proj"
    assert loaded.owner_id == "user_pers"


def test_project_members_and_access(temp_project_dir):
    mgr = ProjectManager(base_storage_dir=temp_project_dir)
    p = mgr.create_project(name="Collaboration Project", owner_id="owner_1")
    pid = p.project_id

    # Add editor and viewer
    mgr.add_member(pid, "editor_1", ProjectRole.EDITOR)
    mgr.add_member(pid, "viewer_1", ProjectRole.VIEWER)

    # Owner has full access
    assert mgr.can_access("owner_1", pid, "read")
    assert mgr.can_access("owner_1", pid, "write")
    assert mgr.can_access("owner_1", pid, "delete")
    assert mgr.can_access("owner_1", pid, "admin")

    # Editor has read, write, execute, link access
    assert mgr.can_access("editor_1", pid, "read")
    assert mgr.can_access("editor_1", pid, "write")
    assert mgr.can_access("editor_1", pid, "execute")
    assert mgr.can_access("editor_1", pid, "link")
    assert not mgr.can_access("editor_1", pid, "delete")
    assert not mgr.can_access("editor_1", pid, "admin")

    # Viewer has read only
    assert mgr.can_access("viewer_1", pid, "read")
    assert not mgr.can_access("viewer_1", pid, "write")
    assert not mgr.can_access("viewer_1", pid, "delete")

    # Non-member has no access
    assert not mgr.can_access("stranger", pid, "read")
    with pytest.raises(ProjectAccessError):
        mgr.require_access("stranger", pid, "read")

    # Remove member
    mgr.remove_member(pid, "viewer_1")
    assert not mgr.can_access("viewer_1", pid, "read")

    # Cannot remove owner
    with pytest.raises(ValueError, match="Cannot remove the project owner"):
        mgr.remove_member(pid, "owner_1")


def test_project_resource_linking(temp_project_dir):
    mgr = ProjectManager(base_storage_dir=temp_project_dir)
    p = mgr.create_project(name="Resource Hub", owner_id="owner_1")
    pid = p.project_id

    # Link conversations
    mgr.link_conversation(pid, "conv_100")
    mgr.link_conversation(pid, "conv_200")
    assert mgr.get_project(pid).conversation_ids == ["conv_100", "conv_200"]

    mgr.unlink_conversation(pid, "conv_100")
    assert mgr.get_project(pid).conversation_ids == ["conv_200"]

    # Link files
    mgr.link_file(pid, "file_abc")
    mgr.link_file(pid, "file_xyz")
    assert mgr.get_project(pid).file_ids == ["file_abc", "file_xyz"]

    mgr.unlink_file(pid, "file_abc")
    assert mgr.get_project(pid).file_ids == ["file_xyz"]


def test_project_workspace_file_operations_and_containment(temp_project_dir):
    mgr = ProjectManager(base_storage_dir=temp_project_dir)
    p = mgr.create_project(name="Workspace Proj", owner_id="owner_1")
    pid = p.project_id

    # Write file safely
    mgr.write_workspace_file(pid, "src/main.py", "print('hello workspace')")
    mgr.write_workspace_file(pid, "README.md", "# Workspace Doc")

    # Read back
    content = mgr.read_workspace_file(pid, "src/main.py")
    assert content == "print('hello workspace')"

    # List files
    files = mgr.list_workspace_files(pid)
    assert files == ["README.md", "src/main.py"]

    # Traversal attempt must fail
    with pytest.raises(ValueError, match="Path traversal detected"):
        mgr.resolve_workspace_path(pid, "../../etc/passwd")

    with pytest.raises(ValueError, match="Path traversal detected"):
        mgr.write_workspace_file(pid, "../escape.txt", "exploit")
