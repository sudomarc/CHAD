"""Concrete CHAD tools (M4).

Filesystem, shell, and Git tools that plug into the runtime via the
``Tool`` protocol defined in ``chad.runtime.tools``. All file operations are
workspace-bound; destructive or process operations require explicit policy.
"""

from .base import BaseTool, ToolSpec, WorkspaceEscape, validate_arguments
from .edit import EditTool
from .fs import GlobTool, GrepTool, ListTool, ReadTool
from .git import GitDiffTool, GitLogTool, GitStatusTool
from .shell import ShellTool

__all__ = [
    "BaseTool",
    "EditTool",
    "GitDiffTool",
    "GitLogTool",
    "GitStatusTool",
    "GlobTool",
    "GrepTool",
    "ListTool",
    "ReadTool",
    "ShellTool",
    "ToolSpec",
    "WorkspaceEscape",
    "validate_arguments",
]
