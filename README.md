# CHAD

**CHAD is the official user-facing conversational application for LapisLLM.**

CHAD owns the user experience: conversations, sessions, history, settings, application commands, and presentation. LapisLLM owns the model and inference runtime.

```text
LapisLLM model/runtime
        ↓ HTTP API
      CHAD application
        ↓
      user
```

## Current foundation

The repository has a layered application core:

```text
chad/
├── core/
│   ├── config.py          # typed application/generation configuration
│   ├── conversation.py    # message ordering and model context
│   └── messages.py        # explicit system/user/assistant messages
├── llm/
│   ├── client.py          # stable application-side LLM boundary
│   ├── http.py            # LapisLLM HTTP API client
│   └── lapis.py           # local developer adapter
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

CHAD uses the **LapisLLM HTTP inference API** as its default user-facing backend. CHAD does not load the Transformer, tokenizer, or checkpoint directly in normal application mode.

Start LapisLLM with one command:

```bash
lapis api serve
```

The API listens on `http://127.0.0.1:8000` by default and exposes:

```text
GET  /v1/models
POST /v1/chat/completions
```

Then start CHAD:

```bash
python -m chad
```

CHAD discovers the available Lapis model through `/v1/models` and sends conversation requests to `/v1/chat/completions`.

For developer-only local integration, `chad.llm.lapis.LocalLapisClient` remains available as a direct runtime adapter. It is not the default user-facing path.

The current Lapis API is non-streaming, so CHAD currently waits for the complete generated response instead of simulating token streaming.

## Configuration

The Lapis API endpoint and model can be overridden with:

```text
CHAD_LAPIS_URL
CHAD_LAPIS_MODEL
CHAD_STORAGE_DIR
CHAD_SYSTEM_PROMPT
CHAD_TEMPERATURE
CHAD_TOP_K
CHAD_TOP_P
CHAD_MAX_NEW_TOKENS
CHAD_DEVELOPER_MODE
```

The default API endpoint is:

```text
http://127.0.0.1:8000
```

Conversations are stored under `~/.chad/conversations` by default.

## Google Colab

With both repositories checked out in the same Colab runtime, the intended flow is:

```bash
cd /content/LapisLLM && pip install -e . && lapis api serve
```

Then, in another cell:

```bash
cd /content/CHAD && pip install -e . && python -m chad
```

For a background API server in one cell:

```bash
cd /content/LapisLLM && pip install -e . && (lapis api serve >/tmp/lapis-api.log 2>&1 &)
```

Then launch CHAD in another cell with:

```bash
cd /content/CHAD && pip install -e . && python -m chad
```

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
CHAD → LapisLLM API
```

The interface hierarchy is:

```text
conversation engine
        ↓
 application state
        ↓
      LLM client
        ↓
   LapisLLM HTTP API
```

This is deliberate so CLI, TUI, web, and desktop interfaces can evolve without moving model logic into presentation code.

## Project status

CHAD is in foundation migration. The official user path is now designed around the LapisLLM HTTP API. Future work will complete command migration, model discovery/switching, real streaming/cancellation when supported by Lapis, richer history UX, and additional interfaces.

## License

See `LICENSE`.
