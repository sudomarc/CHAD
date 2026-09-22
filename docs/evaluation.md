# CHAD evaluation and release gates

## 1. Principle

No competitive claim is valid without reproducible evidence.

Evaluation must test the product system, not only the underlying language model.

## 2. Evaluation layers

### Layer A — Unit correctness

Examples:

- message validation;
- context construction;
- model routing;
- tool schema validation;
- permission enforcement;
- persistence;
- cancellation state transitions.

### Layer B — Backend integration

Verify:

- model discovery;
- generation;
- errors;
- streaming when supported;
- model switching;
- usage metadata;
- timeout behavior.

### Layer C — Tool reliability

Measure:

- correct tool selection;
- valid arguments;
- successful execution;
- malformed-call handling;
- retry behavior;
- permission denials;
- timeout recovery.

### Layer D — Agent tasks

Representative tasks should include:

- research and citation;
- multi-document comparison;
- coding/debugging;
- structured analysis;
- constrained multi-step planning.

### Layer E — Safety

Test:

- prompt injection;
- malicious files;
- hostile retrieved pages;
- secret exfiltration attempts;
- dangerous tool requests;
- sandbox escape attempts;
- excessive autonomy;
- denial/cancellation behavior.

### Layer F — Product UX

Test:

- first-use flow;
- latency perception;
- failed request recovery;
- streaming presentation;
- history;
- mobile/browser layouts later;
- accessibility.

## 3. Internal benchmark taxonomy

Maintain versioned test sets for:

- general knowledge;
- reasoning;
- mathematics;
- coding;
- research;
- long context;
- instruction following;
- tool use;
- file analysis;
- vision;
- French;
- English;
- multilingual prompts;
- safety.

Every benchmark record stores:

- test-set version;
- system version;
- model/provider version;
- configuration;
- timestamp;
- result;
- evaluator version.

## 4. Release gates

A release candidate should not ship when:

- required tests fail;
- a critical security regression exists;
- a previously working integration is broken without an intentional migration;
- tool execution violates its permission contract;
- evaluation data is missing;
- benchmark methodology changed without versioning.

Quality thresholds are defined per task family and should not be invented after seeing results.

## 5. Regression workflow

```text
change
  -> targeted tests
  -> integration tests
  -> evaluation suite
  -> security suite
  -> compare against previous version
  -> inspect regressions
  -> release decision
```

## 6. Online observability

Capture operational metadata needed to investigate:

- latency;
- token usage;
- selected model;
- provider failures;
- tool calls;
- retries;
- cache behavior;
- task completion.

Do not log raw secrets or unrestricted user content by default.

## 7. Model quality claims

Do not state that LapisLLM or CHAD is "better than" a named competitor without a defined benchmark, population/task set, date, methodology and reproducible evidence.

The project may report measured strengths and weaknesses on specific test sets.
