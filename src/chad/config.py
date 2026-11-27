"""Application configuration loading.

Configuration lives in optional ``chad.toml`` files discovered upward from
the workspace, with explicit CLI flags taking precedence. Secrets are never
stored in configuration files: only environment-variable references are
supported if the feature is needed later.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path

CONFIG_NAME = "chad.toml"

# Conservative run limits (docs/agent-runtime.md: required limits).
DEFAULT_MAX_ITERATIONS = 10
DEFAULT_MAX_REQUESTS = 20
DEFAULT_MAX_TOOL_CALLS = 40
DEFAULT_MAX_WALL_CLOCK_SECONDS = 600
DEFAULT_MAX_OUTPUT_BYTES = 1_000_000

_INTEGER_KEYS = (
    "max_iterations",
    "max_requests",
    "max_tool_calls",
    "max_wall_clock_seconds",
    "max_output_bytes",
)

_STRING_KEYS = ("provider", "model", "log_level")


@dataclass(frozen=True)
class Config:
    workspace_root: Path
    provider: str | None = None
    model: str | None = None
    max_iterations: int = DEFAULT_MAX_ITERATIONS
    max_requests: int = DEFAULT_MAX_REQUESTS
    max_tool_calls: int = DEFAULT_MAX_TOOL_CALLS
    max_wall_clock_seconds: int = DEFAULT_MAX_WALL_CLOCK_SECONDS
    max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES
    log_level: str = "INFO"


def _find_config_file(workspace_root: Path) -> Path | None:
    """Walk up from the workspace root looking for ``chad.toml``."""
    directory = workspace_root.resolve()
    for candidate in (directory, *directory.parents):
        config_path = candidate / CONFIG_NAME
        if config_path.is_file():
            return config_path
    return None


def _load_toml(config_path: Path) -> dict:
    with config_path.open("rb") as handle:
        return tomllib.load(handle)


def _apply_section(config: Config, section: dict) -> Config:
    updates: dict = {}
    for key in _STRING_KEYS:
        if key in section:
            updates[key] = str(section[key])
    for key in _INTEGER_KEYS:
        if key in section:
            updates[key] = int(section[key])
    if not updates:
        return config
    return Config(**{**config.__dict__, **updates})


def load_config(
    workspace_root: str | Path | None = None,
    config_path: str | Path | None = None,
) -> Config:
    """Load configuration with explicit precedence.

    Order (lowest to highest): built-in defaults -> ``chad.toml`` discovered
    upward from the workspace -> explicitly passed ``config_path``.
    """
    root = Path(workspace_root).resolve() if workspace_root else Path.cwd().resolve()

    config = Config(workspace_root=root)

    sources: list[Path] = []
    if config_path:
        sources.append(Path(config_path))
    else:
        discovered = _find_config_file(root)
        if discovered is not None:
            sources.append(discovered)

    for source in sources:
        data = _load_toml(source)
        section = data.get("chad", {}) if isinstance(data, dict) else {}
        if isinstance(section, dict):
            config = _apply_section(config, section)

    return config
