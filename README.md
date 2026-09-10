# CHAD

**CHAD is the official user-facing conversational application for LapisLLM.**

CHAD owns the user experience: conversations, sessions, history, settings, application commands, and presentation. LapisLLM owns the model and inference runtime.

```text
LapisLLM
  model + tokenizer + inference runtime
              ↓
            CHAD
  conversations + application state + UI
              ↓
             user
```

## Current foundation

The repository now has a layered application core:

```text
chad/
├── core/
│   ├── config.py          # typed application/generation configuration
│   ├── conversation.py    # message ordering and model context
│   └── messages.py        # explicit system/user/assistant messages
├── llm/
│   ├── client.py          # stable application-side LLM boundary
│   └── lapis.py           # LapisLLM inference adapter
├── storage/
│   └── json_store.py      # replaceable local conversation persistence
├── interfaces/
│   └── cli.py             # conversational CLI
├── app.py                 # application orchestration
└── commands.py            # secondary application controls
```

Natural-language input is model input. Only explicit slash-prefixed controls are commands.

Examples:

```text
hello
Explain transformers
What is Python?
Tell me more
```

Application controls currently include:

```text
/help
/new
/clear
/quit
```

## LapisLLM integration

CHAD uses the public inference boundary exposed by LapisLLM rather than importing Transformer implementation details. The current adapter loads a Lapis checkpoint through `LapisRuntime.from_checkpoint(...)` and delegates generation to the runtime.

The current LapisLLM release exposes non-streaming `generate(...)`. CHAD therefore does not simulate streaming. The client boundary already reserves a real streaming capability for a backend that can provide incremental output.

## Running

CHAD expects an installed LapisLLM environment and a usable inference checkpoint.

```bash
python -m chad
```

or:

```bash
python main.py
```

The default checkpoint is:

```text
checkpoints/latest.pt
```

Configuration can be overridden with environment variables:

```text
CHAD_LAPIS_CHECKPOINT
CHAD_LAPIS_DEVICE
CHAD_STORAGE_DIR
CHAD_SYSTEM_PROMPT
CHAD_TEMPERATURE
CHAD_TOP_K
CHAD_TOP_P
CHAD_MAX_NEW_TOKENS
CHAD_DEVELOPER_MODE
```

Conversations are stored under `~/.chad/conversations` by default.

## Development

Python 3.11+ is required.

```bash
python -m pip install -e ".[test]"
pytest
ruff check .
```

## Architecture rules

CHAD must not contain model architecture, tokenizer internals, training loops, optimizer code, checkpoint-writing logic, or other LapisLLM engineering internals.

The dependency direction is:

```text
CHAD → LapisLLM
```

The interface hierarchy is:

```text
conversation engine
        ↓
 application state
        ↓
     interface
```

This is deliberate so CLI, TUI, web, and desktop interfaces can evolve without moving model logic into presentation code.

## Project status

CHAD is in foundation migration. The previous command-only implementation remains in the repository as legacy material that is no longer the primary application path. Future work will complete command migration, model discovery/switching, real streaming/cancellation when supported by Lapis, richer history UX, and additional interfaces.

## License

See `LICENSE`.
