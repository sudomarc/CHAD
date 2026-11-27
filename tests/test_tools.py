"""Tests for CHAD tools (M4)."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from chad.tools.edit import EditTool
from chad.tools.fs import GlobTool, GrepTool, ListTool, ReadTool
from chad.tools.git import GitDiffTool, GitLogTool, GitStatusTool
from chad.tools.shell import ShellTool


class WorkspaceToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)
        (self.workspace / "a.txt").write_text("hello world\n", encoding="utf-8")
        (self.workspace / "sub").mkdir()
        (self.workspace / "sub" / "b.txt").write_text("foo bar\nfoo baz\n", encoding="utf-8")
        (self.workspace / "sub" / "c.py").write_text("print('hi')\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_read_file(self):
        tool = ReadTool(self.workspace)
        result = tool.call({"path": "a.txt"})
        self.assertEqual(result.output, "hello world\n")

    def test_read_not_a_file(self):
        tool = ReadTool(self.workspace)
        result = tool.call({"path": "sub"})
        self.assertTrue(result.is_error)
        self.assertIn("not a file", result.error)

    def test_read_rejects_traversal(self):
        tool = ReadTool(self.workspace)
        result = tool.call({"path": "../escape.txt"})
        self.assertTrue(result.is_error)
        self.assertIn("escapes workspace", result.error)

    def test_list_directory(self):
        tool = ListTool(self.workspace)
        result = tool.call({"path": "sub"})
        self.assertIn("b.txt", result.output)
        self.assertIn("c.py", result.output)

    def test_grep_finds_matches(self):
        tool = GrepTool(self.workspace)
        result = tool.call({"pattern": "foo"})
        self.assertIn("b.txt", result.output)
        self.assertIn("foo bar", result.output)

    def test_grep_no_matches(self):
        tool = GrepTool(self.workspace)
        result = tool.call({"pattern": "zzz_nope"})
        self.assertEqual(result.output, "(no matches)")

    def test_glob_finds_files(self):
        tool = GlobTool(self.workspace)
        result = tool.call({"pattern": "sub/*.py"})
        self.assertIn("sub/c.py", result.output)
        self.assertNotIn("sub/b.txt", result.output)

    def test_edit_create_and_edit(self):
        tool = EditTool(self.workspace)
        created = tool.call({"operation": "create", "path": "new.txt", "new_string": "beep\n"})
        self.assertEqual(created.output, "created new.txt")
        self.assertTrue((self.workspace / "new.txt").is_file())

        edited = tool.call({
            "operation": "edit",
            "path": "new.txt",
            "old_string": "beep\n",
            "new_string": "boop\n",
        })
        self.assertIn("edited new.txt", edited.output)
        self.assertIn("-beep", edited.output)
        self.assertIn("+boop", edited.output)
        self.assertEqual((self.workspace / "new.txt").read_text(encoding="utf-8"), "boop\n")

    def test_edit_create_already_exists(self):
        tool = EditTool(self.workspace)
        tool.call({"operation": "create", "path": "a.txt", "new_string": "x"})
        result = tool.call({"operation": "create", "path": "a.txt", "new_string": "x"})
        self.assertTrue(result.is_error)
        self.assertIn("already exists", result.error)

    def test_edit_old_string_missing(self):
        tool = EditTool(self.workspace)
        result = tool.call({
            "operation": "edit",
            "path": "a.txt",
            "old_string": "not present",
            "new_string": "x",
        })
        self.assertTrue(result.is_error)
        self.assertIn("not found", result.error)

    def test_shell_success(self):
        tool = ShellTool(self.workspace)
        result = tool.call({"command": [sys.executable, "-c", "print('hello')"]})
        self.assertIsNone(result.error)
        self.assertIn("hello", result.output)

    def test_shell_failing_command(self):
        tool = ShellTool(self.workspace)
        result = tool.call({"command": [sys.executable, "-c", "import sys; sys.exit(3)"]})
        self.assertTrue(result.is_error)
        self.assertIn("exit code 3", result.error)

    def test_validation_rejects_missing_required(self):
        tool = ReadTool(self.workspace)
        result = tool.call({})
        self.assertTrue(result.is_error)
        self.assertIn("missing required argument", result.error)


class GitToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _init_repo(self):
        subprocess.run(
            ["git", "init"],
            cwd=str(self.workspace),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=str(self.workspace),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=str(self.workspace),
            capture_output=True,
            check=True,
        )
        (self.workspace / "file.txt").write_text("v1\n", encoding="utf-8")
        subprocess.run(
            ["git", "add", "file.txt"],
            cwd=str(self.workspace),
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "commit", "-m", "initial"],
            cwd=str(self.workspace),
            capture_output=True,
            check=True,
        )

    def test_git_status_clean(self):
        self._init_repo()
        tool = GitStatusTool(self.workspace)
        result = tool.call({})
        self.assertFalse(result.is_error)
        self.assertIn("clean", result.output.lower())

    def test_git_status_dirty(self):
        self._init_repo()
        (self.workspace / "file.txt").write_text("v2\n", encoding="utf-8")
        tool = GitStatusTool(self.workspace)
        result = tool.call({})
        self.assertFalse(result.is_error)
        self.assertIn("file.txt", result.output)

    def test_git_diff(self):
        self._init_repo()
        (self.workspace / "file.txt").write_text("v2\n", encoding="utf-8")
        tool = GitDiffTool(self.workspace)
        result = tool.call({})
        self.assertFalse(result.is_error)
        self.assertIn("-v1", result.output)
        self.assertIn("+v2", result.output)

    def test_git_log(self):
        self._init_repo()
        tool = GitLogTool(self.workspace)
        result = tool.call({})
        self.assertFalse(result.is_error)
        self.assertIn("initial", result.output)

    def test_git_not_a_repo(self):
        tool = GitStatusTool(self.workspace)
        result = tool.call({})
        self.assertTrue(result.is_error)


if __name__ == "__main__":
    unittest.main()
