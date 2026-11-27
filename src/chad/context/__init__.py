"""Context engine (M5).

Repository discovery, instruction loading, search, context selection and
compaction. Deterministic by design; retrieval does not depend on live model
credentials or external services (docs/testing.md).
"""

from .discovery import (
    InstructionFile,
    discover_roots,
    find_workspace_root,
    load_instruction_files,
)

__all__ = ["InstructionFile", "discover_roots", "find_workspace_root", "load_instruction_files"]
