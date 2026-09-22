# ADR 0002: Use policy-defined specialist agents under one CHAD runtime

## Context

CHAD is evolving from a chat application into a general-purpose agentic system. The ecosystem already has portable engineering-agent policy in Vibe Coding Instructions.

Duplicating generic agent policies inside CHAD would create drift. Splitting each role into an independent runtime would create unnecessary infrastructure and inconsistent state.

## Decision

CHAD uses one shared agent runtime with role-specialized agents:

- Orchestrator
- Researcher
- Coder
- Analyst

Role definitions and reusable policy come from the Vibe Coding Instructions contract layer. CHAD owns runtime execution, state, budgets, permissions and tool mediation.

Agents share:

- model gateway;
- context construction;
- tool registry;
- permission engine;
- memory interfaces;
- observability;
- evaluation.

Agents do not share unconstrained privileges.

## Consequences

- one execution model for retries, cancellation and audit;
- role policies can evolve without duplicating runtime infrastructure;
- cross-role handoffs remain structured;
- security controls are centralized.

The runtime becomes a critical shared subsystem and therefore requires explicit tests and bounded execution.

## Verification / follow-up

- maintain docs/agent-runtime.md;
- keep role contracts versioned in Vibe Coding Instructions;
- add role-specific integration tests;
- add agent-run evaluation and security tests.
