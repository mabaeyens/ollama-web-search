# CLAUDE.md

## Project

**Mira** — local AI assistant with web search, file attachments (PDF/HTML/images), and RAG. CLI + web interface.
- oMLX (default): Qwen3.6-35B-A3B, 262k ctx — inference at `http://localhost:8080`
- Ollama (alt): Gemma4:26b, 64k ctx — inference at `http://localhost:11434`
- Mira web server always on **port 8000** (HTTP) / **8443** (HTTPS), regardless of backend

## Where to look

| Topic | File |
|-------|------|
| Module map, event protocol, RAG, cancel, test patterns | `docs/architecture.md` |
| Config reference, model quirks, full decision log | `DEVELOPMENT.md` |
| Backend/model config | `mira.yaml.example` |
| Commands, hardware specs | `docs/dev-reference.md` |

## Constraints

- Always use `uv` — never `pip` or `venv`.
- Keep all models and search local — no cloud APIs or API keys.
- Do not change `backend` or `MODEL_NAME` in code — use `mira.yaml` instead.
- Do not set `USE_NATIVE_SEARCH = True` — DDGS is a deliberate privacy choice.
- `ChatOrchestrator` must remain display-agnostic — no print/console calls in `orchestrator.py`.
- Tests mock `_call_llm`. Mock chunks need `.message.content`, `.message.tool_calls`, `.done`.
- ChromaDB `EphemeralClient` uses UUID collection names — required.

## Working style

- Proceed without confirmation for file edits and git operations on this repo.
- After any non-trivial fix, write a test before closing the session.
- Bug triage: empty/wrong response → code bug; poor answer despite data → prompt engineering.
