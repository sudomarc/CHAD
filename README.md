# CHAD

**CHAD is the user-facing AI product built around LapisLLM.**

CHAD is intended to evolve from a small conversational application into a general-purpose, tool-using and agentic AI assistant.

```text
                         CHAD
                  user-facing AI product
                           |
                    orchestration
                  /      |       \
             memory     tools    model gateway
                              /      |       \
                         LapisLLM  providers  local models
```

## Project boundary

**CHAD owns**

- conversations and sessions;
- application state and history;
- user-facing interfaces;
- model/provider selection;
- orchestration and agents;
- files and retrieval workflows;
- tool permissions and execution policy;
- memory;
- application-level security and observability.

**LapisLLM owns**

- Transformer/model architecture;
- tokenization;
- training data and training;
- checkpoints;
- native inference/runtime;
- model evaluation;
- model-serving primitives.

Dependency direction:

```text
CHAD → LapisLLM
```

CHAD must not copy Lapis model or training internals, and Lapis must not acquire CHAD consumer-product responsibilities.

## Current foundation

The repository currently contains a Python application core with:

- typed application configuration;
- explicit conversation/message models;
- model discovery;
- an application-side LLM client boundary;
- LapisLLM HTTP integration;
- local JSON conversation persistence;
- CLI interfaces and commands;
- behavioral tests.

The current Lapis integration is non-streaming. CHAD must not simulate streaming by splitting an already completed response.

## Target product

The roadmap turns CHAD into a full AI platform with staged capabilities:

1. robust conversational core;
2. web product;
3. provider-neutral model gateway;
4. web research;
5. file analysis and retrieval;
6. multimodal input;
7. explicit tool platform;
8. sandboxed coding;
9. bounded agent orchestration;
10. user/project memory;
11. accounts, quotas and cost controls;
12. observability and security hardening;
13. continuous evaluation;
14. deeper LapisLLM post-training and scale;
15. connectors and controlled external actions;
16. long-running autonomous workflows.

The project will not claim parity with a named competitor without reproducible evaluation evidence.

## Documentation

- [Documentation index](docs/README.md)
- [Product specification](docs/product-spec.md)
- [Architecture](docs/architecture.md)
- [Exhaustive roadmap](docs/roadmap.md)
- [Model/provider contract](docs/provider-contract.md)
- [Evaluation](docs/evaluation.md)
- [ADR convention](docs/adr/README.md)
- [Engineering contract](AGENTS.md)
- [Security policy](SECURITY.md)

## Running the current foundation

Python 3.11+ is required.

Install:

```bash
python -m pip install -e ".[test]"
```

Run tests:

```bash
pytest
ruff check .
```

Start the Lapis backend:

```bash
lapis api serve
```

Start CHAD:

```bash
python -m chad
```

The current application discovers the available Lapis model through `/v1/models` and sends chat requests to `/v1/chat/completions`.

## Development rule

Roadmap items are plans until implementation and verification exist. Code, tests and runtime evidence are authoritative for implemented behavior.

Before changing architecture, read the relevant documents under `docs/` and preserve the CHAD → LapisLLM boundary.

## License

See [LICENSE](LICENSE).
