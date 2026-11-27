"""Command-line interface entry point for CHAD.

The first usable slice (M1) installs a ``chad`` command, prints version and
help, loads optional configuration, and initializes structured logging.
Starting an agent task (``chad run <task>``) is intentionally rejected with
a clear error until the bounded agent runtime exists.
"""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import __version__
from .config import load_config
from .logging import get_logger, setup_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="chad",
        description="CHAD — local-first general-purpose coding agent.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"chad {__version__}",
    )
    parser.add_argument(
        "--workspace",
        default=".",
        help="Workspace directory (defaults to the current directory).",
    )
    parser.add_argument(
        "--config",
        help="Explicit path to a chad.toml configuration file.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Debug-level structured logging on stderr.",
    )
    subparsers = parser.add_subparsers(dest="command")
    run = subparsers.add_parser(
        "run",
        help="Start an agent task (not implemented in this slice).",
    )
    run.add_argument("task", help="Task description for the agent.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        # argparse exits for --version/--help/errors; keep a stable int code.
        return int(exc.code or 0)

    setup_logging(verbose=args.verbose)
    logger = get_logger("cli")

    config = load_config(workspace_root=args.workspace, config_path=args.config)
    logger.info(
        "chad %s starting (workspace=%s, provider=%s, model=%s)",
        __version__,
        config.workspace_root,
        config.provider,
        config.model,
    )

    if args.command is None:
        parser.print_help(sys.stdout)
        return 0

    if args.command == "run":
        print(
            "error: agent runtime is not yet implemented; use a later slice",
            file=sys.stderr,
        )
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
