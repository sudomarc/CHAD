# Claude Code Instructions for CHAD

This file provides workflow guidance for Claude Code and compatible coding agents. The repository-wide policy in `AGENTS.md` remains authoritative.

## Before changing code
- Read `AGENTS.md` and the relevant documents under `docs/`.
- Inspect the actual repository state; do not rely on an old plan or assumed directory layout.
- Check the current branch and working tree before making changes.

## Project constraints
- CHAD is a local-first general-purpose coding agent.
- The application and orchestration layer are Python-first.
- Rust is reserved for measured performance bottlenecks or isolated native capabilities.
- The user interface is a terminal UI; do not introduce a web frontend without an explicit product decision.
- Model providers are interchangeable through a common capability-aware gateway.
- LapisLLM is a first-class provider, not a hard dependency of the runtime.

## Implementation discipline
- Keep UI, runtime, provider adapters, tools, context, persistence, and security boundaries separate.
- Prefer narrow interfaces, typed inputs/outputs, deterministic tests, and explicit error handling.
- Never simulate streaming when a provider only returns a completed response.
- Do not assume all models support tool calling, vision, structured output, or streaming.
- Ask for confirmation before destructive or externally visible actions unless a policy explicitly authorizes them.
- Do not add placeholder implementations that report success without performing the operation.

## Verification and reporting
- Run the relevant tests and quality checks.
- Inspect the diff and repository status.
- In the final report, distinguish implemented, tested, untested, and deferred work.
- Never claim a command was executed or a behavior verified without evidence.
