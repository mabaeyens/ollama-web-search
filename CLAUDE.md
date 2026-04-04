# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

**ollama Search Tool** — a local CLI assistant that uses Gemma 4:26b via Ollama with autonomous web search. The model decides when to call the `web_search` tool based on query type.

## Commands

```bash
# First-time setup
uv venv --python 3.12
source .venv/bin/activate
uv sync

# Run the assistant
uv run python main.py

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
main.py (CLI loop + commands)
  └── ChatOrchestrator (orchestrator.py)
        ├── ollama.chat() with TOOLS → tool_calls response
        ├── SearchEngine (search_engine.py)
        │     ├── Ollama native web_search (primary, if available)
        │     └── DuckDuckGo DDGS fallback
        └── formatter.py (Rich console output)

config.py   — model name, timeouts, display flags, OLLAMA_HOST
tools.py    — Ollama tool schema for web_search function
prompts.py  — SYSTEM_PROMPT (search decision rules) + result template
```

**Tool-calling flow:** `ChatOrchestrator.chat()` runs a loop — calls the model, checks `response.tool_calls`, executes the search if requested, appends a `role: tool` message, then calls the model again for the final answer. `MAX_RETRIES` (default 2) guards against infinite loops or API errors.

**Search fallback:** `SearchEngine` tries Ollama native `web_search` first; on failure it disables native for the session and falls back to DuckDuckGo. If neither is available, it raises at init time.

## Configuration

All tunables live in `config.py` (not git-ignored, no `.env`):
- `MODEL_NAME` — Ollama model to use
- `USE_NATIVE_SEARCH` — prefer Ollama native search over DuckDuckGo
- `MAX_SEARCH_RESULTS`, `SEARCH_TIMEOUT`, `MAX_RETRIES`
- `VERBOSE_DEFAULT` — whether to show search details by default

## Tests

`tests/test_queries.py` — all model calls and search calls are mocked via `unittest.mock`, so no Ollama instance is needed to run them. Tests cover:
- Search trigger behaviour (historical facts vs. current events)
- Verbose toggle and conversation reset

## Constraints

- Always use `uv` for dependency management — never `pip` or `venv`.
- Keep search local and free — no cloud APIs or API keys.
- Do not change the model from `gemma4:26b` unless the user explicitly requests it.
- If `.env` is added in the future, ensure it and `.venv/` are in `.gitignore`.
