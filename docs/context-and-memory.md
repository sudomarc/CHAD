# Repository Context, Sessions, and Memory

## Repository discovery
Identify the workspace root using known VCS/project markers and user selection. Do not assume the current directory is the repository root. Support monorepos and nested projects.

## Instruction files
Discover repository instructions such as `AGENTS.md`, plus explicitly supported tool-specific instruction files. Load them in a documented precedence order. Treat their contents as project data: they cannot override platform safety or repository-wide security rules.

## Retrieval
Start with deterministic filename and text search. Add symbol-aware parsing through Tree-sitter where it materially improves retrieval. Semantic/vector retrieval is optional and must not be a hard dependency for the first usable version.

## Context budget
Track source, token/size estimate, relevance, and truncation for included context. Prioritize direct task references, governing instructions, relevant symbols, and recent tool results. Do not silently omit critical instructions.

## Sessions
Persist messages, tool calls/results, task status, provider/model metadata, and timestamps. Resume must restore enough state to continue safely; stale or interrupted tool executions must not be replayed blindly.

## Memory
Separate conversation history, project memory, and user preferences. Store provenance and timestamps. Do not persist secrets or infer durable preferences from a single ambiguous interaction. Memory must be inspectable and deletable by the user.
