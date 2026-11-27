# Development Plan

## Delivery strategy
Build a usable vertical slice before expanding breadth. Each milestone should leave the default branch in a coherent, testable state.

## Sequence
1. Governance, package skeleton, CI, and architectural decisions.
2. CLI bootstrap, configuration, and TUI shell.
3. Typed domain contracts and deterministic agent loop.
4. One end-to-end provider adapter and fake provider.
5. Filesystem/search tools and safe tool dispatch.
6. Permission UX and bounded terminal execution.
7. Additional providers and capability-aware model selection.
8. Git and test tools, diff review, and session persistence.
9. Repository context and instruction discovery.
10. Security hardening, skills, memory, and subagents.
11. Profile and selectively implement Rust components.
12. Release packaging, docs, and evaluation suite.

## Definition of done
A task is done when implementation, tests, documentation, error handling, security review, and acceptance criteria are complete. If any item is intentionally deferred, the issue and PR must state it.

## Dependency policy
Prefer standard library and existing dependencies. Add dependencies only with a documented reason, maintenance assessment, license compatibility, and test coverage. Keep optional integrations optional.
