# CHAD

CHAD is a local-first, general-purpose software engineering agent designed to work inside arbitrary local repositories. It combines an interactive terminal interface, a bounded agent runtime, a provider-neutral model gateway, repository-aware tools, and explicit security controls.

**Project status:** active development. Commands and integrations are documented only to the extent implemented and verified. The TUI currently provides a standalone shell; runtime integration is still in progress.

## Installation

The installation guide is maintained at **[sudomarc.github.io/CHAD](https://sudomarc.github.io/CHAD/)**.

- Debian/Ubuntu: use the signed APT repository when the site marks it available.
- Direct Debian package: download the versioned `.deb` linked from the installation site.
- Python source install: use pipx with the optional Textual extra for the TUI.

Do not add an unsigned APT source or disable APT signature verification.

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

- [Installation](docs/installation.md)
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

## Quick start

After installation:

```bash
chad --version
chad --help
chad run "Inspecte ce dépôt et résume sa structure"
```

Without an explicit provider configuration, CHAD uses its deterministic fake provider. Configure a provider and its API key before expecting responses from a real model. See [Installation](docs/installation.md#configuration-dun-fournisseur).

## Development

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e ".[dev]"
python -m unittest discover -s tests
```

The `dev` extra includes Textual so the TUI tests run in CI. The `tui` extra remains available for runtime installations that need the terminal UI.

Read [CONTRIBUTING.md](CONTRIBUTING.md) and [AGENTS.md](AGENTS.md) before contributing.
