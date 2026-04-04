# Project Summary: ollama Search Tool (Gemma 4 + Ollama)

## 1. Original Intent & Goal
To build a **local, private AI assistant** running on macOS that:
- Uses **Gemma 4:26b** (via Ollama) as the core reasoning engine.
- Possesses **autonomous web search capabilities** to answer questions about events after the model's training cutoff (April 2024).
- Decides **when** to search based on query context (ReAct pattern) rather than relying on manual triggers.
- Supports **file attachments** (PDF, HTML, images, text/code) with RAG for large documents.
- Provides both a **CLI interface** and a **local web UI** with streaming markdown responses.
- Runs entirely locally with **zero-cost** search (DuckDuckGo) and no external API keys.

## 2. Technology Stack & Decisions

| Component | Choice | Reasoning |
|-----------|--------|-----------|
| **LLM** | `gemma4:26b` | High reasoning capability, MoE architecture (4b active params), available via Ollama. |
| **Runtime** | Ollama (v0.20.2+) | Native tool calling + multimodal support, local execution. |
| **Language** | Python 3.12+ | Better performance and syntax; 3.9 is EOL. |
| **Package Manager** | `uv` | Fast dependency resolution, reproducible lockfiles. |
| **Search Engine** | DuckDuckGo (`ddgs`) | Free, no API key. Ollama native search disabled (requires paid subscription). |
| **Embeddings** | `nomic-embed-text` via Ollama | Consistent with existing Ollama interface; 768 dims; ~274MB. |
| **Reranker** | CrossEncoder (`cross-encoder/ms-marco-MiniLM-L-6-v2`) | No Ollama reranker available; improves retrieval quality; ~100MB. |
| **Vector store** | ChromaDB `EphemeralClient` (in-memory) | No persistence issues; session-scoped; clean RAM release on reset. |
| **PDF extraction** | PyMuPDF (`fitz`) | Fast, broad format support; validated in prior RAG project. |
| **HTML extraction** | BeautifulSoup | Strips tags cleanly; returns readable text. |
| **CLI UI** | Rich library | Spinners, markdown rendering, formatted output. |
| **Web UI** | FastAPI + SSE + vanilla HTML/JS | No build step, streaming via SSE, markdown via marked.js. |

## 3. Architecture Overview

```
main.py (_render_stream)         server.py (/chat SSE endpoint)
          └────────────────────────────────┘
                        │  consumes events
           ChatOrchestrator.stream_chat()
                        │  yields events
         ┌──────────────┼──────────────┐
   _call_ollama()  SearchEngine    RagEngine
 ollama.chat()      ddgs.text()   index() / query()
                               ┌──────┴──────┐
                         ollama.embed()   ChromaDB
                         (nomic-embed)   EphemeralClient
                                    CrossEncoder reranker
```

**Events yielded by `stream_chat()`:**

| Event | Payload | Meaning |
|-------|---------|---------|
| `thinking` | — | Model is processing |
| `token` | `content` | Answer token |
| `search_start` | `query` | Web search beginning |
| `search_done` | `query, count, results` | Search complete |
| `rag_indexing` | `name` | Document being indexed |
| `rag_done` | `name, chunks` | Indexing complete |
| `warning` | `message` | Non-fatal issue |
| `done` | `content` | Turn complete |
| `error` | `message` | Fatal error |

**System prompt** is built dynamically (`build_system_prompt()`) and includes today's date.

## 4. Key Design Decisions

### A. Autonomous Search
Model decides dynamically based on system prompt rules (date-aware). No hardcoded heuristics.

### B. Search Strategy
- **Active**: `ddgs` (free, no API key).
- **Disabled**: Ollama native `web_search` requires paid subscription — `USE_NATIVE_SEARCH = False`.

### C. File Attachments
- PDFs always go through RAG (consistent behaviour, better accuracy for long docs).
- HTML/text injected directly if ≤ 80k chars; upgraded to RAG above that.
- Images passed via Ollama multimodal `images` field (base64).
- Scanned PDFs detected (empty text layer) and warned rather than silently failing.
- Attachments are single-turn for images/text; RAG index persists across turns.

### D. RAG Design
- Trigger: PDFs always; HTML/text > 80k chars.
- Embeddings: `nomic-embed-text` via `ollama.embed()` batch API.
- Storage: `EphemeralClient()` with UUID collection names (required: ChromaDB 1.x shares Rust backend per process — fixed names collide in tests).
- Retrieval: cosine similarity, top-10 candidates → CrossEncoder reranker → top-4.
- Cross-turn: RAG index queried on every message when non-empty; chunks injected only if CrossEncoder score > 0.0.
- Memory: `clear()` recreates `EphemeralClient` — collection delete alone does not release RAM.
- Reference: existing `github.com/mabaeyens/RAG` repo used as algorithm reference; no code dependency.

### E. Event-Based Architecture
`ChatOrchestrator` is display-agnostic. Single mockable boundary: `_call_ollama()`.

### F. Async/Sync Bridge (Web)
`stream_chat()` is synchronous. FastAPI is async. Bridge: background thread + `asyncio.Queue`.

### G. Environment Management
`uv` (not `pip`/`venv`). `uv venv --python 3.12` → `source .venv/bin/activate` → `uv sync`.

## 5. Current Project Status

### Completed ✅
- **Phase 1** — Core CLI + Web Interface
  - Event-based streaming architecture (`stream_chat()` generator)
  - CLI: Rich spinners, markdown rendering, verbose mode, arrow-key history
  - Web: FastAPI + SSE, live markdown (marked.js), thinking animation, search chips
  - 7 unit tests (all mocked)
- **Phase 2** — File Attachments
  - `file_handler.py`: PDF (PyMuPDF), HTML (BeautifulSoup), images (base64), text
  - Scanned PDF detection, 80k-char context guard
  - CLI: `/attach`, `/files`, `/detach`; Web: 📎 button, file chips, FormData upload
  - `warning` event type for non-fatal issues
- **Phase 3** — RAG
  - `rag_engine.py`: EphemeralClient ChromaDB, nomic-embed-text, CrossEncoder reranker
  - Auto-index on PDF attach; auto-retrieve on every turn when index non-empty
  - CLI: `/rag-list`, `/rag-remove`; Web: indexing chip, green Documents panel
  - `GET /rag/documents`, `DELETE /rag/documents/{name}` endpoints

## 6. File Structure

```
ollama-web-search/
├── main.py              # CLI entry point + _render_stream()
├── server.py            # FastAPI web server + SSE /chat endpoint
├── orchestrator.py      # ChatOrchestrator: stream_chat() generator
├── rag_engine.py        # RagEngine: index, query, remove, clear
├── file_handler.py      # File extraction: PDF, HTML, images, text
├── search_engine.py     # DuckDuckGo search (ddgs)
├── tools.py             # Ollama tool schema for web_search
├── prompts.py           # build_system_prompt() — date-aware
├── formatter.py         # Rich console helpers (CLI only)
├── config.py            # All tunables including RAG_* knobs
├── pyproject.toml       # uv project config
├── uv.lock              # Locked dependencies
├── .gitignore
├── README.md
├── CLAUDE.md
├── PROJECT_SUMMARY.md
├── DEVELOPMENT.md       # Development log with decisions and rationale
├── TEST_PLAN.md         # Structured web UI test plan
├── static/
│   └── index.html       # Web UI (vanilla HTML/CSS/JS + marked.js)
└── tests/
    ├── conftest.py       # sys.path injection
    └── test_queries.py   # 7 unit tests
```

## 7. Roadmap

### Phase 4 — Backlog

- **Show RAG chunks in web UI**: When a response uses RAG, show the source chunks (filename, score) that were injected. UI pattern: collapsible "Sources" section below the assistant bubble. Already tracked in backlog.

### Phase 5 — Future (not planned)

- **Scanned PDF OCR**: Detect scanned PDFs and run OCR (e.g. `tesseract`) to extract text before indexing.
- **Persistent RAG index**: Optionally persist the ChromaDB index to disk so documents survive session restarts.

## 8. Backlog

- **Show RAG chunks in web UI** — When a response is generated from RAG retrieval, show the source chunks (filename, score) that were injected so the user can verify where the answer came from. UI pattern: collapsible "Sources" section below the assistant bubble.

## 9. Notes for Claude Code Context

- Always use `uv` — never `pip` or `venv`.
- Keep all models and search local — no cloud APIs or API keys.
- Do not change `MODEL_NAME` from `gemma4:26b` unless explicitly requested.
- Do not set `USE_NATIVE_SEARCH = True` — Ollama native requires a paid subscription.
- Do not change `EMBED_MODEL` from `nomic-embed-text` unless explicitly requested.
- `ChatOrchestrator` must remain display-agnostic — no print/console calls in `orchestrator.py`.
- Tests mock `_call_ollama`, not higher-level methods. Mock chunks need `.message.content`, `.message.tool_calls`, `.done`.
- ChromaDB `EphemeralClient` uses UUID collection names — required due to shared Rust backend in ChromaDB 1.x.
