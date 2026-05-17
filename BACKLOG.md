# Backlog

## Pending

### Harness quality
- [ ] Parallel tool execution — orchestrator runs only the first tool call per step; if the model emits multiple tool calls in one response, the rest are dropped; execute all in parallel and merge results before the next turn
- [ ] Shell timeout 30s → configurable per-call — long builds and test suites time out; add optional `timeout` arg to `run_shell` (cap at e.g. 300s)

### Future / nice-to-have
- [ ] Scanned PDF OCR — detect scanned PDFs (empty text layer) and run OCR (e.g. `tesseract`) before indexing
- [ ] Persistent RAG index — ChromaDB `PersistentClient` option so documents survive server restarts

## Notes

- Projects have three modes: local-only (local_path only), GitHub-only (github_repo only), or both. Tool availability depends on local_path — no local path means fs/shell tools are hidden from the model entirely
- workspace_root flows per-call through all fs_tools and shell_tools via a `root` parameter; shell sandbox pattern rebuilt per-call from the active root (not cached at import time)
- `_LOCAL_TOOLS` set in tools.py drives filtering in orchestrator._active_tools — add new local-only tools there
- `DB_PATH` in `core/config.py` — database lives at `~/.local/share/mira/conversations.db`
- The `mira-server` skill copies plist from `~/Documents/Projects/mira-core/com.mab.mira.plist`; reload required any time the plist or server paths change
- Mac app bundle ID remains `com.mab.OllamaSearch` (no rebuild needed for Python-side refactors)
- `_ollama_ready` is set True after the warm-up loop regardless of success/failure — app never hangs indefinitely if Ollama is permanently down
- Model validation at startup uses `client.list()` (all installed models), not `client.ps()` (only in-memory loaded models) — do not revert
