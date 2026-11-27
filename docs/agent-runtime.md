# Agent Runtime Specification

## Responsibility
The runtime coordinates a task from user request to verified outcome. It owns state transitions, model calls, tool dispatch, budgets, cancellation, and final reporting. It does not own terminal rendering or provider-specific HTTP details.

## Core cycle
1. Accept a user task and workspace context.
2. Resolve applicable trusted instructions and relevant repository context.
3. Build a provider request from typed messages and available tool schemas.
4. Receive a model response and validate its structure.
5. If the response requests tools, validate each call, evaluate policy, request approval when required, execute, and append structured results.
6. Re-evaluate until completion, cancellation, or a configured limit.
7. Report actions, changed files, verification results, and remaining uncertainty.

## Required limits
Every run must have configurable maximum iterations, model requests, tool calls, wall-clock duration, output bytes, and concurrency. Defaults must be conservative. Exhaustion must produce an explicit stopped state, not an apparent success.

## State model
A task can be pending, running, waiting_for_permission, completed, failed, or cancelled. Invalid transitions must be rejected. A failed tool call is data for the next reasoning step; it must not be silently converted to success.

## Tool-call handling
- Validate tool name and arguments against a registered schema.
- Reject unknown tools and malformed arguments.
- Apply policy before execution.
- Execute with timeout and cancellation support.
- Capture exit status, bounded stdout/stderr, duration, and structured metadata.
- Return an explicit error result on failure.

## Provider behavior
The runtime consumes normalized provider responses. It must honor provider capability declarations and never emulate unsupported streaming or tool calling as if native.

## Final response contract
The final report must distinguish actions performed, files changed, checks actually run, results, and unverified items. The runtime must not infer success from a model's claim.
