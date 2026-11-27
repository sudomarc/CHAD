# Contributing to CHAD

Thank you for contributing. CHAD is being developed as a secure, local-first coding agent. Contributions should preserve clear subsystem boundaries and verifiable behavior.

## First steps
1. Read `AGENTS.md` and the relevant specifications in `docs/`.
2. Check existing issues before starting substantial work.
3. For significant changes, open or update an issue describing the problem, scope, and acceptance criteria.
4. Create a focused branch from the current default branch.
5. Keep changes small enough to review.

## Development principles
- Python owns application orchestration, runtime behavior, providers, TUI, and most integrations.
- Rust is introduced only for a justified native component with a stable boundary.
- Provider-specific API details belong in provider adapters.
- Tools must have validated input schemas, structured results, timeouts, and permission classifications.
- UI code must not contain agent policy or provider-specific logic.
- Avoid unnecessary abstractions and premature optimization.

## Change requirements
- Add tests for new behavior and regression tests for bug fixes.
- Update documentation when public behavior, configuration, security, or architecture changes.
- Do not commit credentials, tokens, private datasets, local session databases, or generated secrets.
- Do not silently change defaults or compatibility contracts.
- Do not mark roadmap items complete until the implementation and relevant tests are verified.

## Pull request checklist
- [ ] The change solves the linked issue and stays within its scope.
- [ ] Relevant instructions and documentation were followed.
- [ ] Tests cover the changed behavior.
- [ ] Formatting, linting, type checks, and tests were run where applicable.
- [ ] Security and permission implications were considered.
- [ ] Documentation and examples are accurate.
- [ ] The diff contains no secrets, unrelated changes, or generated noise.
- [ ] The PR states what was tested and what remains unverified.

## Commit and PR style
Use clear, imperative commit messages. Pull requests should explain the problem, the approach, trade-offs, verification commands, and known limitations. Link related issues with GitHub closing keywords only when the PR truly completes them.
