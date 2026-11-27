# CHAD Roadmap

This roadmap describes intended milestones, not implemented capabilities. An item is complete only when its acceptance criteria are met, tests pass, and the documentation reflects the shipped behavior.

## M0 — Project foundation
- Repository governance and contributor workflow.
- Product and architecture specifications.
- Python/Rust boundary and quality gates.
- CI baseline and issue taxonomy.

## M1 — Minimal application and TUI
- Installable Python package and CLI entry point.
- TUI shell with input, transcript, status, and cancellation.
- Configuration loading and diagnostics.
- Structured application logging.

## M2 — Agent runtime
- Typed conversation and event models.
- Bounded observe/decide/act loop.
- Tool-call parsing and dispatch.
- Cancellation, budgets, timeouts, and failure handling.
- Deterministic tests using fake providers and tools.

## M3 — Model gateway
- Provider-neutral request/response contract.
- LapisLLM, OpenAI, Anthropic, and Google adapters as separately scoped integrations.
- Capability discovery and model selection.
- Native streaming where supported.
- Usage and provider error normalization.

## M4 — Core development tools
- Workspace-aware filesystem read/list/search.
- Safe file creation and editing.
- Terminal execution with policy checks.
- Git status and diff.
- Test and lint command execution.

## M5 — Repository context
- Repository discovery and ignore rules.
- Instruction-file loading with trust boundaries.
- Symbol-aware search and optional syntax parsing.
- Context budgeting and compaction.
- Exclusion of secrets and irrelevant large files.

## M6 — Security and reliability
- Permission policies and approval UX.
- Process lifecycle and cancellation.
- Workspace boundary enforcement.
- Secret redaction and audit events.
- OS-backed isolation evaluation and documented threat model.

## M7 — Sessions, memory, and skills
- SQLite session persistence and resume.
- Project-level memory with explicit provenance.
- User-defined skills and hooks with permission controls.
- Import/export and cleanup behavior.

## M8 — Subagents and extensibility
- Bounded delegated tasks.
- Shared artifact references and isolated contexts.
- Concurrency and budget limits.
- External tool protocol evaluation.

## M9 — Rust components and release
- Profile Python hot paths before porting.
- Introduce Rust only where measurements justify it.
- Packaging, release automation, compatibility policy, and benchmark suite.

## Non-goals for early milestones
- Web application or hosted multi-tenant service.
- Model training or fine-tuning infrastructure.
- Unbounded autonomous execution.
- Mandatory vector database.
- Full parity with any commercial coding agent.

## Status policy
Use GitHub milestones and issues as the operational source of truth. Do not infer completion from this document or from merged documentation alone.
