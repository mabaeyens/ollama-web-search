# Backlog

## Done
- [2026-04-25] /health returns 503 during Ollama warm-up — added _ollama_ready flag; 503+{"status":"starting"} while model loads, 200+{"status":"ok"} once ready; macOS native app splash stays visible until model is warmed
- [2026-04-25] shell sandbox: run_shell rejects absolute paths outside WORKSPACE_ROOT — closes escape where cwd was sandboxed but command args (ls /, cat /etc/passwd) were not
- [2026-04-25] prompt Rule 1: model answers capability questions from system prompt without calling tools
- [2026-04-25] Fixed Mac app "couldn't read data" error: LaunchAgent was still running from old `ollama-web-search/` path after refactor — reloaded with `mira-core` plist
- [2026-04-25] Cleaned up stale db files at repo root and backup after confirming all conversations intact
- [2026-04-25] Fixed missing conversations: after `core/` refactor, `DB_PATH` resolves to `core/conversations.db` — merged old root-level db (12 conversations) into new location
- [2026-04-25] Updated `mira-server` skill plist source path from `ollama-web-search` to `mira-core`
- [2026-04-25] Refactored all core modules into `core/` package (Option A architecture)
- [2026-04-25] Updated plist paths to `mira-core`; added `AssociatedBundleIdentifiers` to plist

## Pending

## Notes
- `DB_PATH = Path(__file__).parent / "conversations.db"` in `core/config.py` means the database lives at `mira-core/core/conversations.db`, not the repo root — be aware when backing up
- The `mira-server` skill copies plist from `~/Documents/Projects/mira-core/com.mab.mira.plist`; reload is required any time the plist or server paths change
- Mac app bundle ID remains `com.mab.OllamaSearch` (no rebuild needed for Python-side refactors)
- _ollama_ready is set True after the warm-up loop regardless of success/failure — app never hangs indefinitely if Ollama is permanently down; it just gets a working server with a broken first chat rather than a stuck splash
