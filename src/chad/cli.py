"""Command-line interface entry point for CHAD.

The first usable slice (M1) installs a ``chad`` command, prints version and
help, loads optional configuration, and initializes structured logging.
Starting an agent task (``chad run <task>``) is intentionally rejected with
a clear error until the bounded agent runtime exists.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from chad.runtime.tools import Tool, ToolRegistry

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
        help="Execute an agent task using the bounded agent runtime.",
    )
    run.add_argument("task", help="Task description for the agent.")
    tui = subparsers.add_parser(
        "tui",
        help="Launch the terminal user interface shell.",
    )
    tui.add_argument(
        "--standalone",
        action="store_true",
        help="Run the shell without a runtime (echoes input).",
    )
    return parser


def _build_tool_registry(workspace_root) -> ToolRegistry:
    """Build a tool registry with safe, workspace-bound default tools.

    Read-only tools are included by default; write/dangerous tools require
    explicit policy, which the CLI does not grant by default.
    """
    from chad.runtime.tools import ToolRegistry
    from chad.tools import GlobTool, GrepTool, ListTool, ReadTool

    registry = ToolRegistry()
    for tool_cls in (ReadTool, ListTool, GrepTool, GlobTool):
        registry.register(tool_cls(workspace_root))  # type: ignore[arg-type]
    return registry


def _build_provider(config):
    """Build a model provider from configuration.

    Falls back to the fake provider when no real provider is configured or
    when its credentials are missing. This keeps ``chad run`` functional
    without credentials while demonstrating the full runtime pipeline.
    """
    from chad.gateway import (
        AnthropicProvider,
        FakeProvider,
        GoogleProvider,
        LapisLLMProvider,
        OpenAIProvider,
    )
    from chad.gateway.errors import GatewayError

    provider_name = config.provider or "fake"

    builders = {
        "openai": lambda: OpenAIProvider(
            api_key=os.getenv("OPENAI_API_KEY"), base_url=None
        ),
        "anthropic": lambda: AnthropicProvider(
            api_key=os.getenv("ANTHROPIC_API_KEY"), base_url=None
        ),
        "google": lambda: GoogleProvider(
            api_key=os.getenv("GOOGLE_API_KEY"), base_url=None
        ),
        "lapisllm": lambda: LapisLLMProvider(
            api_key=os.getenv("LAPISLLM_API_KEY"), base_url=None
        ),
    }

    if provider_name in builders:
        try:
            return builders[provider_name]()
        except GatewayError as exc:  # no credential or provider error
            print(
                f"warning: could not initialize {provider_name} provider: {exc}",
                file=sys.stderr,
            )
            print(
                "falling back to fake provider (no real model will be called)",
                file=sys.stderr,
            )
            return FakeProvider()

    # Unknown provider name -> fake provider, so the CLI still runs.
    print(
        f"warning: unknown provider {provider_name!r}; using fake provider",
        file=sys.stderr,
    )
    return FakeProvider()


class ReadOnlyPolicy:
    """Policy allowing only read-only tools by default.

    Safe for a first ``chad run`` implementation: no files are modified and
    no processes are started without explicit user configuration.
    """

    READ_ONLY: ClassVar[set[str]] = {
        "read",
        "list",
        "grep",
        "glob",
        "git_status",
        "git_diff",
        "git_log",
    }

    def allows(self, tool: Tool, arguments: dict[str, Any]) -> bool:
        return getattr(tool, "name", "") in self.READ_ONLY


def _format_report(report, final_answer: str | None = None) -> str:
    """Render a human-readable task report."""
    lines = [
        f"CHAD task {report.task_id}",
        f"  status:      {report.status.value}",
        f"  outcome:     {report.outcome.value}",
        f"  iterations:  {report.iterations}",
        f"  requests:    {report.requests}",
        f"  tool calls:  {report.tool_calls}",
        f"  wall clock:  {report.wall_clock_seconds:.2f}s",
    ]
    if report.error:
        lines.append(f"  error:       {report.error}")
    if report.actions:
        lines.append("  actions:")
        for action in report.actions:
            lines.append(
                f"    - {action.kind} {action.target}: {'ok' if action.ok else 'failed'}"
                + (f" ({action.detail})" if action.detail else "")
            )
    if report.results:
        lines.append("  results:")
        for result in report.results:
            lines.append(f"    - {result.name}: {'ok' if not result.is_error else 'error'}")
            if result.error:
                lines.append(f"        {result.error}")
            elif result.output is not None:
                preview = result.output[:200]
                if len(result.output) > 200:
                    preview += "..."
                lines.append(f"        {preview}")
    if report.unverified:
        lines.append("  unverified:")
        for item in report.unverified:
            lines.append(f"    - {item}")
    if final_answer:
        lines.append("  final answer:")
        lines.append(f"    {final_answer}")
    return "\n".join(lines)


def run_task(args, config) -> int:
    """Execute an agent task end-to-end.

    Builds the task, provider, tool registry and policy, runs the bounded
    agent loop, and prints a structured report.
    """
    from chad.runtime.loop import AgentLoop, LoopLimits
    from chad.runtime.task import Task

    # Limits from configuration.
    limits = LoopLimits(
        max_iterations=config.max_iterations,
        max_requests=config.max_requests,
        max_tool_calls=config.max_tool_calls,
        max_wall_clock_seconds=config.max_wall_clock_seconds,
        max_output_bytes=config.max_output_bytes,
    )

    task = Task(id="cli-1", description=args.task)

    registry = _build_tool_registry(config.workspace_root)
    provider = _build_provider(config)
    policy = ReadOnlyPolicy()

    loop = AgentLoop(
        task=task,
        provider=provider,
        registry=registry,
        model=config.model,
        policy=policy,
        limits=limits,
    )

    report = loop.run()

    # Extract the assistant's final answer from the task messages, if any.
    final_answer = None
    for msg in reversed(loop.task.messages):
        if msg.role.value == "assistant":
            final_answer = msg.content
            break

    print(_format_report(report, final_answer))

    # Exit code reflects outcome.
    if report.outcome.name in ("COMPLETED",):
        return 0
    if report.outcome.name in ("WAITING_FOR_PERMISSION",):
        return 1
    return 2


def run_tui(args) -> int:
    """Launch the Textual TUI shell.

    Textual is imported lazily so the core package stays installable without
    the TUI dependency (see the ``tui`` extra in pyproject.toml).
    """
    from .tui.app import ChadApp

    app = ChadApp()
    return int(app.run() or 0)


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
        return run_task(args, config)

    if args.command == "tui":
        return run_tui(args)

    return 0


if __name__ == "__main__":
    sys.exit(main())
