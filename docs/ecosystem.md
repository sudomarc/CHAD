
# CHAD ecosystem

CHAD is the agent runtime and user-facing product in the three-repository AI ecosystem.

~~~text
Vibe Coding Instructions
  governance / skills / role contracts
                 |
                 v
CHAD
  orchestration / agents / tools / memory / UX
                 |
                 v
LapisLLM
  model / training / inference / runtime
~~~

| System | Owns | Does not own |
|---|---|---|
| Vibe Coding Instructions | agent governance, skills, evidence rules, token economics, self-improvement policy, role contracts | runtime execution, user accounts, model weights |
| CHAD | product UI/API, conversations, orchestration, agents, tools, permissions, files, memory, model gateway | Transformer internals and training |
| LapisLLM | model architecture, tokenizer, training, checkpoints, inference, generation, runtime metadata, model evaluation | consumer UX, agent orchestration, user memory |

CHAD may consume selected policies and role contracts from Vibe Coding Instructions. The framework is not a second runtime.

CHAD consumes LapisLLM through its public runtime/API boundary. Product code must not import Lapis model or training internals.

Material cross-repository contract changes require synchronized documentation and compatibility tests.

A source file existing in one repository is not evidence that a connected capability works end-to-end.

## Release coordination

Record compatible versions/commits when a release depends on another repository.

A cross-repository release note should identify:

- CHAD version/commit;
- LapisLLM version/commit;
- Vibe Coding Instructions version/commit when relevant;
- supported capabilities;
- known incompatibilities;
- verification evidence.

## Primary repositories

- https://github.com/sudomarc/vibe-coding-instructions
- https://github.com/sudomarc/CHAD
- https://github.com/sudomarc/LapisLLM
