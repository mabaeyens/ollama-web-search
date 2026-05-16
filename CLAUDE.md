# CLAUDE.md

## Project

**Mira** — local AI assistant with autonomous web search, file attachments (PDF/HTML/images/text), and RAG for large documents. CLI + local web interface. Default stack: oMLX + Qwen3.6-35B-A3B (262k context). Ollama + Gemma4:26b also supported.

## Reference docs — read when working on these subsystems

| File | When to read |
|------|-------------|
| `docs/architecture.md` | Event protocol, RAG internals, cancel mechanism, DDGS rationale, test mock patterns |
| `hardware-specs.md` | M5 hardware specs and Ollama env var rationale |
| `DEVELOPMENT.md` | Full decision log and build history |
| `mira.yaml.example` | External config template — copy to `mira.yaml` to switch backends/models |

## Commands

```bash
uv sync                                               # install dependencies
python main.py                                        # CLI
python server.py                                      # web interface → http://localhost:8000
uv add <package>                                      # add dependency
uv run python -m pytest --tb=short -q                 # all tests (no LLM server needed)
uv run python -m pytest tests/test_queries.py::test_name  # single test
```

Default backend: oMLX at `http://localhost:8000` with Qwen3.6-35B-A3B.
Ollama fallback: set `backend: ollama` in `mira.yaml`, requires `gemma4:26b` and `nomic-embed-text`.
Override host with `OLLAMA_HOST` env var.

## Architecture

```
main.py (CLI)     server.py (FastAPI + SSE)
        └─────────────────┘
                 │
      core/orchestrator.py → ChatOrchestrator
            │  stream_chat(user_message, attachments=None, thinking_enabled=True) → yields events
            ├── _call_llm() → ollama.chat() OR openai.chat.completions.create()
            ├── core/search_engine.py → SearchEngine → ddgs.text()
            └── core/rag_engine.py → RagEngine
                      ├── ollama.embed() OR openai.embeddings.create() (EMBED_BACKEND)
                      ├── chromadb.EphemeralClient (in-memory)
                      └── CrossEncoder (sentence-transformers)

core/config.py       — all tunables; loads overrides from mira.yaml (git-ignored)
core/file_handler.py — load_file() / load_file_bytes(): PDF→RAG, HTML→text, image→base64
core/tools.py        — OpenAI-compatible tool schema for web_search and all tools
core/prompts.py      — build_system_prompt() injects today's date + search rules
core/formatter.py    — Rich console helpers (CLI only)
core/db.py           — SQLite conversation persistence
core/workspace.py    — sandbox path enforcement
core/fs_tools.py     — filesystem tool implementations
core/shell_tools.py  — shell execution tool
core/github_tools.py — GitHub API tool
static/index.html    — single-page web UI (vanilla HTML/CSS/JS + marked.js)
```

Events yielded by `stream_chat()`: `thinking`, `token`, `search_start/done`, `fetch_start/done/context`, `rag_indexing/done/context`, `stats`, `warning`, `done`, `error`. Full payload schema in `docs/architecture.md`.

**RAG:** PDFs always go through RAG. HTML/text > 80k chars also go through RAG. When files are indexed in the current turn, score threshold is bypassed (`float('-inf')`) to prevent hallucination on meta-instructions like "summarize this" — do not remove this. Full explanation in `docs/architecture.md`.

**Cancel:** `POST /cancel` sets a `threading.Event`; `produce()` breaks out; `event_stream()` rolls back `conversation_history` to pre-turn length. Details in `docs/architecture.md`.

**`<think>` tags:** Qwen3.6 streams reasoning inside `<think>…</think>` blocks. The streaming loop detects these and strips them from `full_content` / `token` events. Thinking content is silently consumed (not emitted to UI). This is intentional — do not remove.

## Configuration

**External config (preferred):** copy `mira.yaml.example` → `mira.yaml` and edit. The file is git-ignored. Fields:
- `backend` — `omlx` (default) or `ollama`
- `model` — model name as shown in the backend
- `host` — LLM server URL
- `embed_backend`, `embed_model`, `embed_host` — embedding backend (defaults to LLM backend)
- `context_window` — token context (262144 for Qwen3.6-35B-A3B, 65536 for Gemma4:26b)

**Fallback defaults in `core/config.py`** (not git-ignored):
- `USE_NATIVE_SEARCH`, `MAX_SEARCH_RESULTS`, `SEARCH_TIMEOUT`, `MAX_RETRIES`, `MAX_TOOL_STEPS`
- `VERBOSE_DEFAULT`
- `RERANK_MODEL` — `cross-encoder/ms-marco-MiniLM-L-6-v2` (sentence-transformers)
- `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_RETRIEVE_K`, `RAG_RERANK_TOP_K`, `RAG_SCORE_THRESHOLD`, `RAG_MAX_CHUNKS`

## Constraints

- Always use `uv` — never `pip` or `venv`.
- Keep all models and search local — no cloud APIs or API keys.
- Do not change `backend` or `MODEL_NAME` in code — use `mira.yaml` instead.
- Do not set `USE_NATIVE_SEARCH = True` — DDGS is a deliberate privacy choice (see `docs/architecture.md`).
- `ChatOrchestrator` must remain display-agnostic — no print/console calls in `orchestrator.py`.
- Tests mock `_call_llm`, not higher-level methods. Mock chunks need `.message.content`, `.message.tool_calls`, `.done`.
- ChromaDB `EphemeralClient` uses UUID collection names — required; fixed names cause collisions in tests.

## Working style

**Proceed without confirmation** for file edits and git operations on this repo.

**After any non-trivial fix, write a test before closing the session.**

**Bug triage:**
- Empty/wrong response → code bug (streaming, tool call handling, SSE)
- Poor answer despite having data → prompt engineering, not code

**Model quirks:**
- Gemma4 (Ollama): emits `tool_calls` in an intermediate chunk (`done=False`) — handled by `accumulated_tool_calls` in `orchestrator.py`.
- Gemma4 (Ollama): occasionally emits LaTeX (e.g. `$\rightarrow$`) — `preprocessLatex()` in `index.html` converts to Unicode.
- Qwen3.6 (oMLX): emits `<think>…</think>` blocks — stripped in the streaming loop in `orchestrator.py`.
- Qwen3.6 (oMLX): tool calls arrive assembled in the done chunk (OpenAI streaming format).
