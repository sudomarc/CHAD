# ADR-0001: Python-first application with a selective Rust boundary

- Status: Accepted
- Date: 2026-11-27
- Owners: CHAD maintainers

## Context
CHAD is intentionally a hybrid-language project. Its agent runtime, provider integrations, TUI, configuration, and most tools benefit from Python's iteration speed and ecosystem. Some workloads may later benefit from native performance or OS-level integration.

## Options considered
1. Implement the whole application in Python.
2. Split the application broadly between Python and Rust from the beginning.
3. Keep the product Python-first and introduce Rust only for measured, isolated needs.

## Decision
Choose option 3. Python owns orchestration and product behavior. Rust is introduced only for a demonstrated performance bottleneck or a clearly bounded native capability. The Python/Rust interface must remain small, typed, and independently testable.

## Consequences
- The initial project can remain Python-only without violating the hybrid decision.
- Rust packaging and cross-platform support are added only when justified.
- Benchmarks must precede performance-driven ports.
- Rust must not become a second orchestration layer.

## Revisit when
A representative workload demonstrates a material bottleneck or an OS capability that cannot be implemented safely and maintainably in Python.
