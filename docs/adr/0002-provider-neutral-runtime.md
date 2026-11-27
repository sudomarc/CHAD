# ADR-0002: Keep the agent runtime provider-neutral

- Status: Accepted
- Date: 2026-11-27
- Owners: CHAD maintainers

## Context
CHAD must support multiple model providers, including LapisLLM, without tying task execution or tool policy to one vendor's request format.

## Options considered
1. Use one provider SDK directly throughout the runtime.
2. Normalize all providers behind a shared contract and preserve explicit capability metadata.
3. Restrict the application to an OpenAI-compatible API shape.

## Decision
Choose option 2. The runtime consumes normalized contracts. Each provider adapter maps its API to those contracts and reports actual per-model capabilities. Provider-specific features may be exposed through explicit extensions but must not silently alter core semantics.

## Consequences
- Provider adapters require contract tests.
- Unsupported capabilities remain explicit.
- Model portability improves at the cost of adapter maintenance.
- LapisLLM remains first-class without becoming a runtime dependency.

## Revisit when
A concrete provider feature cannot be represented without damaging the common contract; any extension must be documented and isolated.
