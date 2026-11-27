"""Tests for the CHAD CLI entry point."""

from __future__ import annotations

import io
import unittest
from unittest.mock import patch

from chad.cli import main
from chad import __version__


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
        code, out, err = self.run_main(["--help"])
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

    def test_run_not_implemented(self):
        code, out, err = self.run_main(["run", "inspect the repository"])
        self.assertNotEqual(code, 0)
        self.assertEqual(out, "")
        self.assertIn("not yet implemented", err)


if __name__ == "__main__":
    unittest.main()
