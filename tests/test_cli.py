"""Tests for the CHAD CLI entry point."""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from chad import __version__
from chad.cli import main


class CliTests(unittest.TestCase):
    def run_main(self, args):
        stdout = io.StringIO()
        stderr = io.StringIO()
        with patch("sys.stdout", stdout), patch("sys.stderr", stderr):
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_version_flag(self):
        code, out, err = self.run_main(["--version"])
        self.assertEqual(code, 0)
        self.assertIn(f"chad {__version__}", out)
        self.assertEqual(err, "")

    def test_help_flag(self):
        code, out, _err = self.run_main(["--help"])
        self.assertEqual(code, 0)
        self.assertIn("chad", out)
        self.assertIn("--version", out)

    def test_unknown_argument(self):
        code, _, _ = self.run_main(["--bogus"])
        self.assertEqual(code, 2)

    def test_no_command_prints_help(self):
        code, out, _ = self.run_main([])
        self.assertEqual(code, 0)
        self.assertIn("run", out)

    def test_run_executes_task_with_fake_provider(self):
        code, out, _err = self.run_main(["run", "list the workspace files"])
        self.assertEqual(code, 0)
        self.assertIn("CHAD task", out)
        self.assertIn("outcome:", out)
        self.assertIn("completed", out)


if __name__ == "__main__":
    unittest.main()
