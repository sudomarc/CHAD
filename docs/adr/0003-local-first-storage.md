# ADR-0003: Use local-first persistence

- Status: Accepted
- Date: 2026-11-27
- Owners: CHAD maintainers

## Context
CHAD is designed to operate inside arbitrary local repositories. A mandatory hosted service would add availability, privacy, and operational dependencies.

## Options considered
1. Require a remote database and account service.
2. Store all state in ad hoc JSON files.
3. Use local SQLite for structured session data and ordinary files for human-authored configuration and memory.

## Decision
Choose option 3. SQLite is the initial store for sessions and structured event history. TOML and Markdown remain the preferred formats for user-editable configuration, rules, and skills.

## Consequences
- Core workflows can work offline apart from model-provider access.
- Schema migrations and local data lifecycle need explicit handling.
- Secrets must never be persisted in session records.
- Backup, export, and deletion behavior must be documented.

## Revisit when
A real multi-device or collaboration requirement justifies an optional synchronization layer.
