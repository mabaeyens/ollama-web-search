# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ollama Search Tool** — a local AI assistant using Gemma 4:26b via Ollama with autonomous web search. Available as both a CLI tool and a local web interface. The model decides when to call the `web_search` tool based on query type (ReAct pattern).

## Commands

```bash
# First-time setup
uv venv --python 3.12
source .venv/bin/activate
uv sync

# Pull required Ollama models
ollama pull gemma4:26b
ollama pull nomic-embed-text   # used for RAG embeddings

# Run the CLI
python main.py

# Run the web interface (open http://localhost:8000)
python server.py

# Add a dependency
uv add <package>

# Run all tests (no Ollama needed — model calls are mocked)
uv run pytest

# Run a single test
uv run pytest tests/test_queries.py::test_toggle_verbose
```

Requires Ollama running locally (`http://localhost:11434` by default) with `gemma4:26b` pulled. Override with `OLLAMA_HOST` env var.

## Architecture

```
main.py (CLI loop + _render_stream)     server.py (FastAPI + SSE)
         └──────────────────────────────────────┘
                         │
              ChatOrchestrator (orchestrator.py)
                    │  stream_chat() → yields events
                    ├── _call_ollama() → ollama.chat(stream=True)
                    └── SearchEngine (search_engine.py)
                              └── DuckDuckGo (ddgs)

config.py    — model name, timeouts, display flags, OLLAMA_HOST
tools.py     — Ollama tool schema for web_search function
prompts.py   — build_system_prompt() injects today's date + search rules
formatter.py — Rich console helpers (CLI only)
static/index.html — single-page web UI (vanilla HTML/CSS/JS + marked.js)
```

**Event-based streaming flow:** `ChatOrchestrator.stream_chat()` is a generator that yields typed events:
- `{"type": "thinking"}` — model is processing
- `{"type": "token", "content": "..."}` — answer token (streamed)
- `{"type": "search_start", "query": "..."}` — search beginning
- `{"type": "search_done", "query": "...", "count": N, "results": [...]}` — search complete
- `{"type": "done", "content": "..."}` — turn complete, full answer
- `{"type": "error", "message": "..."}` — error occurred

The CLI (`_render_stream` in `main.py`) and web server (`/chat` SSE endpoint in `server.py`) consume the same events differently.

**Mockable boundary:** `_call_ollama()` is the single point tests mock — returns an iterable of stream chunks.

**Search:** Ollama native search is disabled (`USE_NATIVE_SEARCH = False`) — it requires a paid Ollama subscription. DuckDuckGo (`ddgs`) is the active search engine.

## Configuration

All tunables live in `config.py` (not git-ignored, no `.env`):
- `MODEL_NAME` — Ollama model to use
- `USE_NATIVE_SEARCH` — `False` (Ollama native requires paid subscription)
- `MAX_SEARCH_RESULTS`, `SEARCH_TIMEOUT`, `MAX_RETRIES`, `MAX_TOOL_STEPS`
- `VERBOSE_DEFAULT` — whether to show search details by default
- `OLLAMA_HOST` — override via env var

## Tests

`tests/test_queries.py` — all model and search calls mocked via `unittest.mock`. No Ollama instance needed.

Mock pattern: `patch.object(orchestrator, '_call_ollama', return_value=iter([chunk]))` where each chunk is a `MagicMock` with `.message.content`, `.message.tool_calls`, `.done`.

Tests cover: search trigger behaviour, search_done event payload, verbose toggle, conversation reset.

## Constraints

- Always use `uv` for dependency management — never `pip` or `venv`.
- Keep search local and free — no cloud APIs or API keys.
- Do not change the model from `gemma4:26b` unless the user explicitly requests it.
- Do not set `USE_NATIVE_SEARCH = True` — Ollama native search requires a paid subscription.
- If `.env` is added in the future, ensure it and `.venv/` are in `.gitignore`.
