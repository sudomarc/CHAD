# Tools and Permission Model

## Tool contract
Every tool declares a stable identifier, purpose, validated input schema, structured output, risk classification, timeout, and permission requirement. Tool implementations must be independently testable.

## Initial tool groups
- Filesystem: list, read, create, edit, move, delete.
- Search: filename/glob and content search.
- Terminal: process execution and lifecycle.
- Git: status, diff, log, branch inspection.
- Validation: test, lint, type-check command execution.

## Permission levels
- **Read-only:** inspect workspace content and metadata.
- **Ask:** request approval for modifications, process execution, network access, or other policy-sensitive operations.
- **Policy-authorized:** perform only actions explicitly covered by a user-configured policy.

No mode grants unrestricted access by default. Destructive actions, writes outside the workspace, credential access, privilege escalation, and external side effects require explicit safeguards.

## Workspace boundaries
Resolve paths canonically and reject traversal, symlink escapes, and paths outside configured roots unless separately authorized. Re-check boundaries at execution time to reduce time-of-check/time-of-use risks.

## Shell execution
Do not construct shell commands by concatenating untrusted strings. Prefer argument arrays and explicit working directories. If a shell is required, make the shell boundary explicit, bound output/runtime, and apply policy to the actual command.

## Approval UX
Approval requests must show the exact action, target paths/command, reason, and scope of authorization. A one-time approval must not silently become permanent permission.

## Isolation
A permission prompt is not a sandbox. Any sandbox claim must identify the OS mechanism, isolation boundary, network policy, filesystem policy, and tested limitations.
