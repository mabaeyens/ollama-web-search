# CLAUDE.md

## Project

**Mira** — local AI assistant with autonomous web search, file attachments (PDF/HTML/images/text), and RAG for large documents. CLI + local web interface. Default stack: oMLX + Qwen3.6-35B-A3B (262k context). Ollama + Gemma4:26b also supported.

## Reference docs

| File | When to read |
|------|-------------|
| `docs/architecture.md` | Module map, event protocol, RAG internals, cancel, config reference, model quirks, test patterns |
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
