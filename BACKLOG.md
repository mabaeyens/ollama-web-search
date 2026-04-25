# Backlog

## Done
- [2026-04-25] edit_file(path, old_str, new_str) — targeted string-replace patch tool; rejects if old_str matches zero or >1 locations; prefer over write_file for existing files
- [2026-04-25] github_create_pr(repo, title, body, head, base) — opens a PR; base defaults to repo default branch
- [2026-04-25] github_merge_pr(repo, pr_number, merge_method) — merges PR with confirmation gate; supports merge/squash/rebase
- [2026-04-25] MAX_TOOL_STEPS 5 → 10 — end-to-end coding flows (read→edit→commit→PR→merge) no longer hit the ceiling
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

### Harness quality
- [ ] Parallel tool execution — orchestrator runs only the first tool call per step; if the model emits multiple tool calls in one response, the rest are dropped; execute all in parallel and merge results before the next turn
- [ ] Shell timeout 30s → configurable per-call — long builds and test suites time out; add optional `timeout` arg to `run_shell` (cap at e.g. 300s)

### Project / workspace switching
- [ ] Per-conversation workspace — `WORKSPACE_ROOT` is a process-global env var; add a `workspace_root` column to the conversations DB so each conversation can be scoped to a different folder; set at conversation creation, shown in the app sidebar
- [ ] `GET /workspaces` + `POST /workspace` endpoints — let the iOS/macOS app list recently used workspaces and switch the active one; persist the list to disk (JSON sidecar next to the DB)
- [ ] App project picker UI — sidebar section "Projects" showing recent workspaces; tap to open a new conversation scoped to that folder; "New project" action lets user type an absolute path or a GitHub repo URL (clone on demand into ~/workspace/<name>)
- [ ] `github_clone_repo(repo, dest)` tool — wraps `git clone` into the workspace sandbox; enables "open this repo as a project" from within chat without leaving the app

## Notes
- `DB_PATH = Path(__file__).parent / "conversations.db"` in `core/config.py` means the database lives at `mira-core/core/conversations.db`, not the repo root — be aware when backing up
- The `mira-server` skill copies plist from `~/Documents/Projects/mira-core/com.mab.mira.plist`; reload is required any time the plist or server paths change
- Mac app bundle ID remains `com.mab.OllamaSearch` (no rebuild needed for Python-side refactors)
- _ollama_ready is set True after the warm-up loop regardless of success/failure — app never hangs indefinitely if Ollama is permanently down; it just gets a working server with a broken first chat rather than a stuck splash
