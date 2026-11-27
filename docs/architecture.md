# Architecture

## Goals
CHAD is a local-first coding agent with a TUI, a Python orchestration layer, interchangeable model providers, repository tools, and explicit security policy. The architecture must work across repositories without assuming a particular language or framework.

## High-level components
1. **CLI/bootstrap:** process startup, configuration, workspace selection, lifecycle.
2. **TUI:** presentation and user interaction; consumes runtime events and submits user actions.
3. **Agent runtime:** conversation state, planning cycle, tool orchestration, budgets, cancellation.
4. **Model gateway:** provider-neutral contracts and provider adapters.
5. **Tool system:** validated capabilities for filesystem, shell, Git, search, and tests.
6. **Context engine:** repository discovery, instruction loading, search, context selection, compaction.
7. **Security:** permission decisions, workspace policy, secret handling, audit trail, isolation integration.
8. **Persistence:** sessions, event history, configuration metadata, and project memory.
9. **Native core (optional):** Rust components only where measured performance or OS integration warrants them.

## Dependency direction
Presentation -> application/runtime interfaces -> domain contracts. Provider adapters and tool implementations depend on contracts, not the other way around. The runtime must not import TUI implementation details. Provider adapters must not own session state or tool policy.

## Python/Rust boundary
Python is the default implementation language. Rust components must expose a small, typed, versioned boundary and remain optional where practical. Use PyO3/maturin only when an actual native extension is justified. Do not create a Rust workspace solely to satisfy the hybrid-language decision.

## Runtime events
The runtime emits typed events such as user message accepted, model request started, tool requested, permission required, tool completed, iteration completed, and task finished/failed/cancelled. The TUI renders these events but does not determine their meaning or policy.

## Persistence
Start with SQLite for sessions and structured history, plus TOML configuration and ordinary files for user-authored rules/skills. Avoid requiring a remote database. Define migrations before schema changes become routine.

## Key quality attributes
- Testability without live model credentials.
- Provider portability and capability awareness.
- Observable and cancellable execution.
- Safe filesystem and process handling.
- Predictable resource budgets.
- Recoverable sessions.
- Minimal mandatory dependencies.

## Architecture decisions
Significant choices must be recorded as ADRs under `docs/adr/` using the template in `docs/adr/0000-template.md`. Decisions should state context, options, decision, consequences, and revisit conditions.
