"""Repository discovery and instruction-file loading (M5, issue #75).

The workspace root is identified using VCS/project markers, never assumed to
be the current directory. Monorepos and nested projects are supported: every
directory carrying a marker is a candidate root, ordered nearest-to-farthest
from the start path.

Repository instruction files (e.g. ``AGENTS.md``) are loaded as project data:
their contents are returned verbatim with source provenance. They cannot
override platform safety or repository-wide security rules — enforcement lives
in the permission layer, not here.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# VCS markers and project markers, checked bottom-up from the start path.
_VCS_MARKERS = (".git", ".hg", ".svn")
_PROJECT_MARKERS = (
    "chad.toml",
    "AGENTS.md",
    "CLAUDE.md",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "package.json",
)
_ALL_MARKERS = _VCS_MARKERS + _PROJECT_MARKERS

# Documented precedence of instruction files within a workspace root.
# Lower index = higher priority; nearest root wins over an ancestor root.
INSTRUCTION_FILES = ("AGENTS.md", "CLAUDE.md", "chad.toml")


@dataclass(frozen=True)
class InstructionFile:
    """A discovered repository instruction file, with provenance."""

    path: Path
    name: str
    text: str
    precedence: int  # lower = higher priority


def _has_marker(directory: Path) -> bool:
    return any((directory / marker).exists() for marker in _ALL_MARKERS)


def discover_roots(start: str | Path) -> list[Path]:
    """Return all directories above ``start`` (inclusive) that carry a marker.

    Ordered nearest-to-farthest. Stops at the filesystem root. Symlinked
    directories are resolved canonically so traversal cannot escape the real
    workspace boundary.
    """
    directory = Path(start).resolve()
    roots: list[Path] = []
    seen: set[Path] = set()
    while True:
        canonical = directory.resolve()
        if canonical in seen:
            break
        seen.add(canonical)
        if _has_marker(canonical):
            roots.append(canonical)
        parent = canonical.parent
        if parent == canonical:  # reached filesystem root
            break
        directory = parent
    return roots


def find_workspace_root(start: str | Path | None = None) -> Path | None:
    """Return the nearest directory carrying a marker, or ``None``.

    ``start`` defaults to the current working directory.
    """
    roots = discover_roots(Path.cwd() if start is None else start)
    return roots[0] if roots else None


def load_instruction_files(root: str | Path) -> list[InstructionFile]:
    """Load instruction files from a workspace root in documented precedence.

    Files missing from the root are skipped. Contents are raw text; the
    caller decides how to use them — they do not alter platform policy.
    """
    directory = Path(root).resolve()
    instructions: list[InstructionFile] = []
    for precedence, name in enumerate(INSTRUCTION_FILES):
        path = directory / name
        if path.is_file():
            instructions.append(
                InstructionFile(
                    path=path,
                    name=name,
                    text=path.read_text(encoding="utf-8"),
                    precedence=precedence,
                )
            )
    instructions.sort(key=lambda item: item.precedence)
    return instructions
