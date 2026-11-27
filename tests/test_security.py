"""Security tests (M6, issue #77).

Positive and negative tests for workspace path traversal, symlink escape,
shell command policy (argument arrays only), output limits, cancellation,
and secret redaction.
"""

from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from chad.runtime.contracts import ToolCall, ToolResult
from chad.runtime.loop import AgentLoop, LoopLimits
from chad.runtime.provider import ModelResponse
from chad.runtime.task import Task
from chad.runtime.tools import ToolRegistry
from chad.security.redaction import DEFAULT_SECRET_PATTERNS, Redactor, redact_secrets
from chad.tools.base import WorkspaceEscape, resolve_within
from chad.tools.shell import ShellTool


def _supports_symlinks() -> bool:
    try:
        with tempfile.TemporaryDirectory() as td:
            link = Path(td) / "link"
            try:
                link.symlink_to(td)
                return True
            except (OSError, NotImplementedError):
                return False
    except OSError:
        return False


CAN_SYMLINK = _supports_symlinks()


class PathTraversalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_legitimate_path_resolves_inside_workspace(self):
        target = resolve_within(self.workspace, "sub", "file.txt")
        self.assertEqual(target, self.workspace / "sub" / "file.txt")
        self.assertIn(self.workspace, target.parents)

    def test_dotdot_traversal_is_rejected(self):
        with self.assertRaises(WorkspaceEscape):
            resolve_within(self.workspace, "..", "outside.txt")
        with self.assertRaises(WorkspaceEscape):
            resolve_within(self.workspace, "sub", "..", "..", "etc", "passwd")

    @unittest.skipUnless(CAN_SYMLINK, "symlink creation not permitted on this host")
    def test_symlink_escape_is_rejected(self):
        outside = tempfile.mkdtemp()
        secret = Path(outside) / "secret.txt"
        secret.write_text("sneaky", encoding="utf-8")
        link = self.workspace / "link.txt"
        link.symlink_to(secret)
        try:
            with self.assertRaises(WorkspaceEscape):
                resolve_within(self.workspace, "link.txt")
        finally:
            link.unlink()


class ShellPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workspace = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_command_is_argument_array_never_shell_string(self):
        tool = ShellTool(self.workspace)
        captured = {}

        def fake_run(*args, **kwargs):
            captured["args"] = args
            captured["kwargs"] = kwargs
            return MagicMock(returncode=0, stdout="ok", stderr="")

        with patch("chad.tools.shell.subprocess.run", side_effect=fake_run):
            tool.call({"command": ["echo", "hello world"]})

        self.assertIsInstance(captured["args"][0], list)
        self.assertEqual(captured["args"][0], ["echo", "hello world"])
        self.assertIs(captured["kwargs"].get("shell", False), False)

    def test_unlistable_string_command_rejected_by_schema(self):
        tool = ShellTool(self.workspace)
        result = tool.call({"command": "echo hello"})
        self.assertTrue(result.is_error)
        self.assertIn("must be an array", result.error)


class _AllowPolicy:
    def allows(self, tool: object, arguments: dict) -> bool:
        return True


class OutputLimitTests(unittest.TestCase):
    def test_long_tool_output_is_truncated(self):
        workspace = tempfile.mkdtemp()
        try:
            tool_registry = ToolRegistry()

            class BigOutputTool:
                def __init__(self) -> None:
                    self.name = "big"
                    self.description = "returns a lot"
                    self.input_schema: dict = {}

                def call(self, arguments: dict) -> ToolResult:
                    return ToolResult(
                        tool_call_id="tc",
                        name="big",
                        output="x" * 1000,
                    )

            tool_registry.register(BigOutputTool())

            class StatefulProvider:
                def __init__(self) -> None:
                    self.calls = 0

                def request(self, model: str, messages, tool_schemas):
                    self.calls += 1
                    if self.calls == 1:
                        return ModelResponse(
                            content="go",
                            tool_calls=(ToolCall(id="tc-1", name="big"),),
                        )
                    return ModelResponse(content="done")

            task = Task(id="t-1", description="big output")
            loop = AgentLoop(
                task=task,
                provider=StatefulProvider(),
                registry=tool_registry,
                policy=_AllowPolicy(),
                limits=LoopLimits(max_output_bytes=100),
            )
            report = loop.run()
            self.assertEqual(report.outcome.name, "COMPLETED")
            result = loop.task.results[0]
            self.assertTrue("[output truncated" in result.output)
            self.assertEqual(len(result.output), 100 + len("\n...[output truncated]"))
        finally:
            shutil.rmtree(workspace)


class CancellationTests(unittest.TestCase):
    def test_cancel_stops_loop(self):
        workspace = tempfile.mkdtemp()
        try:
            tool_registry = ToolRegistry()

            class OneShotProvider:
                def request(self, messages, tool_schemas):
                    from chad.runtime.contracts import ModelResponse
                    return ModelResponse(content="done")

            task = Task(id="t-1", description="cancel me")
            loop = AgentLoop(task=task, provider=OneShotProvider(), registry=tool_registry)
            loop.cancel()
            report = loop.run()
            self.assertEqual(report.outcome.name, "CANCELLED")
            self.assertEqual(task.status.name, "CANCELLED")
        finally:
            import shutil

            shutil.rmtree(workspace)


class RedactionTests(unittest.TestCase):
    def test_secret_patterns_are_redacted(self):
        samples = [
            "api_key = sk-1234567890abcdef",
            "Authorization: Bearer ya29.xyz",
            "password=supersecret123",
            "SECRET_KEY := notasecret",
        ]
        for sample in samples:
            redacted = redact_secrets(sample)
            self.assertNotEqual(redacted, sample)
            self.assertIn("[REDACTED]", redacted)

    def test_plain_text_unchanged(self):
        normal = "print('hello world')\nx = 42\n"
        self.assertEqual(redact_secrets(normal), normal)

    def test_default_patterns_non_empty(self):
        self.assertGreaterEqual(len(DEFAULT_SECRET_PATTERNS), 3)

    def test_redactor_counts_redactions(self):
        redactor = Redactor()
        redactor.redact("api_key = aaa")
        redactor.redact("token = bbb")
        self.assertEqual(redactor.redact_count, 2)


if __name__ == "__main__":
    unittest.main()
