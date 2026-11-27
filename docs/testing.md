# Testing and Quality Strategy

## Test layers
- **Unit:** pure logic, schemas, policy decisions, state transitions, path validation.
- **Contract:** provider adapters, tool interfaces, persistence repositories.
- **Integration:** runtime with fake providers/tools and temporary workspaces.
- **End-to-end:** CLI/TUI workflows against deterministic fixtures.
- **Security:** traversal, symlink escape, secret redaction, command policy, cancellation, output limits.
- **Performance:** only for identified hot paths and representative workloads.

## Determinism
Default CI must not require live model credentials or external services. Use fake providers and recorded sanitized fixtures. Live provider tests are opt-in.

## Required regression coverage
Every fixed bug should gain a test that fails before the fix where practical. Security boundary changes require positive and negative tests.

## Quality gates
The exact tools and commands will be finalized in the initial implementation issue. At minimum, CI should run formatting/lint, static type checks where configured, unit tests, integration tests, and Rust checks when Rust code exists.

## Reporting
Record commands and exit status. A skipped test is not a passing test. A mocked provider test does not prove live provider compatibility.
