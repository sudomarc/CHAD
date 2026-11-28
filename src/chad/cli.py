"""Command-line interface entry point for CHAD.

The terminal UI is the primary interface. Running ``chad`` without arguments
launches the interactive TUI. A non-interactive ``run`` mode remains
available for automation and scripting.
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
        help="Execute an agent task using the bounded agent runtime (non-interactive).",
    )
    run.add_argument("task", help="Task description for the agent.")
    subparsers.add_parser(
        "tui",
        help="Launch the terminal user interface shell (default when no command given).",
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


def run_tui(args, config) -> int:
    """Launch the Textual TUI shell connected to the agent runtime."""
    from chad.runtime.loop import AgentLoop, LoopLimits
    from chad.runtime.task import Task
    from chad.runtime.tools import ToolRegistry
    from chad.tools import GlobTool, GrepTool, ListTool, ReadTool

    from .tui.app import ChadApp

    # Build tool registry with read-only tools
    registry = ToolRegistry()
    for tool_cls in (ReadTool, ListTool, GrepTool, GlobTool):
        registry.register(tool_cls(config.workspace_root))  # type: ignore[arg-type]

    # Build provider
    provider = _build_provider(config)

    # Build limits from config
    limits = LoopLimits(
        max_iterations=config.max_iterations,
        max_requests=config.max_requests,
        max_tool_calls=config.max_tool_calls,
        max_wall_clock_seconds=config.max_wall_clock_seconds,
        max_output_bytes=config.max_output_bytes,
    )

    # Create TUI app with runtime integration
    class TUIRuntime:
        def __init__(self):
            self._loop: AgentLoop | None = None
            self._task: Task | None = None
            self._on_submit_callback = None
            self._on_cancel_callback = None

        def submit(self, task_description: str) -> None:
            """Submit a new task to the agent loop."""

            self._task = Task(id="tui-1", description=task_description)
            self._loop = AgentLoop(
                task=self._task,
                provider=provider,
                registry=registry,
                model=config.model,
                policy=ReadOnlyPolicy(),
                limits=limits,
                on_event=self._on_event,
            )

            if self._on_submit_callback:
                self._on_submit_callback()

            # Run the loop in a background thread
            import threading

            def run_loop():
                report = self._loop.run()
                # Emit completion event
                self._emit_completion(report)

            thread = threading.Thread(target=run_loop, daemon=True)
            thread.start()

        def cancel(self) -> None:
            """Cancel the current task."""
            if self._loop:
                self._loop.cancel()

        def _on_event(self, event):
            """Handle runtime events and forward to TUI."""
            if self._on_event_callback:
                self._on_event_callback(event)

        def _emit_completion(self, report):
            """Emit task completion."""
            if self._on_completion_callback:
                self._on_completion_callback(report)

    runtime = TUIRuntime()

    app = ChadApp(runtime=runtime)
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

    # Default to TUI when no command is given; preserve explicit tui command
    # But allow non-interactive mode for automation/testing
    if args.command is None or args.command == "tui":
        import sys
        if not sys.stdin.isatty():
            # Non-interactive environment: print help instead of launching TUI
            parser.print_help(sys.stdout)
            return 0
        return run_tui(args, config)

    if args.command == "run":
        return run_task(args, config)

    return 0


if __name__ == "__main__":
    sys.exit(main())
