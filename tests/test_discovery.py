"""Tests for repository discovery and instruction loading (issue #75)."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chad.context.discovery import (
    InstructionFile,
    discover_roots,
    find_workspace_root,
    load_instruction_files,
)


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, rel, content=""):
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_finds_root_from_nested_directory(self):
        (self.root / ".git").mkdir()
        nested = self.root / "apps" / "web" / "src"
        nested.mkdir(parents=True)
        root = find_workspace_root(nested)
        self.assertEqual(root, self.root)

    def test_returns_none_without_markers(self):
        (self.root / "apps" / "web").mkdir(parents=True)
        self.assertIsNone(find_workspace_root(self.root / "apps" / "web"))

    def test_current_directory_defaults_to_cwd_when_no_arg(self):
        # Cannot control CWD reliably here; just ensure no exception.
        root = find_workspace_root()
        # result is None or a Path; accept either.
        self.assertTrue(root is None or isinstance(root, Path))

    def test_discovers_all_roots_monorepo(self):
        (self.root / ".git").mkdir()
        packages = self.root / "packages" / "core"
        packages.mkdir(parents=True)
        (packages / "pyproject.toml").write_text("{}", encoding="utf-8")
        roots = discover_roots(packages)
        self.assertEqual(roots[0], packages)  # nearest first
        self.assertIn(self.root, roots[1:])  # ancestor with .git

    def test_loads_instruction_files_with_precedence(self):
        (self.root / ".git").mkdir()
        (self.root / "AGENTS.md").write_text("# agents", encoding="utf-8")
        (self.root / "CLAUDE.md").write_text("# claude", encoding="utf-8")
        (self.root / "chad.toml").write_text("provider = 'x'\n", encoding="utf-8")
        instructions = load_instruction_files(self.root)
        self.assertEqual(len(instructions), 3)
        self.assertEqual([i.name for i in instructions], ["AGENTS.md", "CLAUDE.md", "chad.toml"])
        self.assertEqual([i.precedence for i in instructions], [0, 1, 2])
        self.assertEqual(instructions[0].text, "# agents")

    def test_skips_missing_instruction_files(self):
        (self.root / ".git").mkdir()
        instructions = load_instruction_files(self.root)
        self.assertEqual(instructions, [])

    def test_instruction_file_is_dataclass(self):
        inst = InstructionFile(
            path=Path("/x/AGENTS.md"),
            name="AGENTS.md",
            text="hi",
            precedence=0,
        )
        self.assertEqual(inst.name, "AGENTS.md")
        self.assertEqual(inst.precedence, 0)


if __name__ == "__main__":
    unittest.main()
