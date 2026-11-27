# CHAD

CHAD is a local-first, general-purpose software engineering agent designed to work inside arbitrary local repositories. It combines an interactive terminal interface, a bounded agent runtime, a provider-neutral model gateway, repository-aware tools, and explicit security controls.

**Current status:** project foundation and specifications. Features described in the roadmap are planned until implemented and verified.

## Product decisions
- **Languages:** Python for orchestration and product logic; Rust for justified native components.
- **Interface:** terminal UI (TUI).
- **Models:** multi-provider, capability-aware gateway.
- **Scope:** general-purpose development work across local repositories and technology stacks.
- **Deployment model:** local-first; no mandatory hosted CHAD service.

## Product principles
1. The agent must inspect before it changes.
2. Tool execution must be observable, bounded, and permission-aware.
3. Provider capabilities must be explicit rather than assumed.
4. Changes must be reviewable and testable.
5. The runtime must remain independent from the terminal UI and any one model provider.
6. Security and truthful reporting are product requirements.

## Documentation
- [Agent instructions](AGENTS.md)
- [Claude Code instructions](CLAUDE.md)
- [Contributing](CONTRIBUTING.md)
- [Roadmap](ROADMAP.md)
- [Security policy](SECURITY.md)
- [Architecture](docs/architecture.md)
- [Agent runtime](docs/agent-runtime.md)
- [Model providers](docs/model-providers.md)
- [Tools and permissions](docs/tools-and-permissions.md)
- [Context and memory](docs/context-and-memory.md)
- [Testing strategy](docs/testing.md)
- [Development plan](docs/development-plan.md)

## Planned user experience
From a repository directory, the user will eventually be able to start CHAD, ask it to inspect or modify the project, review proposed changes, authorize tools, run tests, and resume previous sessions.

The exact command and installation experience will be finalized with the first working CLI milestone.

## Development status
The repository is being rebuilt from an empty Git tree. Do not assume that the architecture, modules, commands, or capabilities in these documents already exist. Track implementation through GitHub issues and update this README as verified functionality lands.

## Contributing
Read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) before submitting changes.
