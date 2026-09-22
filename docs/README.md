# CHAD documentation

CHAD is the user-facing AI product built around LapisLLM.

## Documentation map

| Document | Purpose |
|---|---|
| [Product specification](product-spec.md) | Product vision, V1 scope, non-goals, UX and capability requirements |
| [Architecture](architecture.md) | Target system boundaries, components, data flows and deployment topology |
| [Roadmap](roadmap.md) | Exhaustive phased implementation plan and exit criteria |
| [Model/provider contract](provider-contract.md) | Provider-neutral LLM interface and model routing contract |
| [Evaluation](evaluation.md) | Quality, safety, reliability and regression evaluation system |
| [Context](context.md) | Conversation context budgeting and truncation behavior |
| [Compatibility](compatibility.md) | Current cross-repository capability matrix |

## Source-of-truth rules

- Code and tests are authoritative for implemented behavior.
- Documentation is authoritative for intended architecture and planned scope.
- A planned capability must not be described as implemented until code and verification support it.
- LapisLLM remains the model/training/runtime project.
- CHAD remains the user-facing application and orchestration layer.

## Current state

The repository currently contains a small Python conversational application with a Lapis HTTP client, conversation engine, local JSON persistence, configuration, commands, CLI interface, and tests.

The larger agentic architecture described here is the target system. It is intentionally staged so each capability can be implemented and verified independently.
