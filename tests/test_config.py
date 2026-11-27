"""Tests for application configuration loading."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from chad.config import (
    DEFAULT_MAX_ITERATIONS,
    DEFAULT_MAX_OUTPUT_BYTES,
    DEFAULT_MAX_REQUESTS,
    DEFAULT_MAX_TOOL_CALLS,
    DEFAULT_MAX_WALL_CLOCK_SECONDS,
    load_config,
)

_TOML = """[chad]
provider = "lapisllm"
model = "lapis-1"
max_iterations = 5
max_requests = 12
max_tool_calls = 60
max_wall_clock_seconds = 300
max_output_bytes = 500000
log_level = "DEBUG"
"""


class ConfigTests(unittest.TestCase):
    def test_defaults_without_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = load_config(workspace_root=tmp)
        self.assertEqual(config.workspace_root, Path(tmp).resolve())
        self.assertIsNone(config.provider)
        self.assertIsNone(config.model)
        self.assertEqual(config.max_iterations, DEFAULT_MAX_ITERATIONS)
        self.assertEqual(config.max_requests, DEFAULT_MAX_REQUESTS)
        self.assertEqual(config.max_tool_calls, DEFAULT_MAX_TOOL_CALLS)
        self.assertEqual(config.max_wall_clock_seconds, DEFAULT_MAX_WALL_CLOCK_SECONDS)
        self.assertEqual(config.max_output_bytes, DEFAULT_MAX_OUTPUT_BYTES)
        self.assertEqual(config.log_level, "INFO")

    def test_loads_discovered_config_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "chad.toml").write_text(_TOML, encoding="utf-8")
            config = load_config(workspace_root=workspace)
        self.assertEqual(config.provider, "lapisllm")
        self.assertEqual(config.model, "lapis-1")
        self.assertEqual(config.max_iterations, 5)
        self.assertEqual(config.max_requests, 12)
        self.assertEqual(config.max_tool_calls, 60)
        self.assertEqual(config.max_wall_clock_seconds, 300)
        self.assertEqual(config.max_output_bytes, 500000)
        self.assertEqual(config.log_level, "DEBUG")

    def test_discovers_config_in_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            nested = workspace / "nested" / "deep"
            nested.mkdir(parents=True)
            (workspace / "chad.toml").write_text(
                '[chad]\nprovider = "anthropic"\n', encoding="utf-8"
            )
            config = load_config(workspace_root=nested)
        self.assertEqual(config.provider, "anthropic")

    def test_explicit_config_path_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "chad.toml").write_text(
                '[chad]\nprovider = "discovered"\n', encoding="utf-8"
            )
            explicit = workspace / "explicit.toml"
            explicit.write_text(
                '[chad]\nprovider = "explicit"\nmodel = "m-1"\n', encoding="utf-8"
            )
            config = load_config(workspace_root=workspace, config_path=explicit)
        self.assertEqual(config.provider, "explicit")
        self.assertEqual(config.model, "m-1")


if __name__ == "__main__":
    unittest.main()
