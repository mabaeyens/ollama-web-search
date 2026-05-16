# omlx-ctl

Command-line manager for the oMLX inference server. Installed at `~/.local/bin/omlx-ctl`.

## Commands

| Command | Description |
|---------|-------------|
| `omlx-ctl start` | Start oMLX on port 8080, wait until API is ready, then print status |
| `omlx-ctl stop` | Graceful stop (SIGTERM → SIGKILL after 10 s) |
| `omlx-ctl restart` | Stop then start |
| `omlx-ctl status` | Show process PID, API reachability, loaded models, and ready flag |
| `omlx-ctl logs` | Last 50 lines from `/tmp/omlx.log` |

`omlx-ctl` with no argument defaults to `status`.

## Status output

```
=== oMLX Status ===
Process : running (PID 12345)
API     : reachable (http://localhost:8080)
Models  :
  - Qwen3.6-35B-A3B
Ready   : YES — Qwen3.6-35B-A3B available
```

**Ready: YES** means the configured model (`Qwen3.6-35B-A3B`) is loaded and accepting requests. This is the same check Mira's `/health` endpoint uses for `backend_ready`.

## API key

oMLX requires authentication. The script reads the API key from `~/.omlx/settings.json` (`auth.api_key`) and includes it as `Authorization: Bearer <key>` on every request. No manual configuration needed.

## Internals

- Detects the process with `pgrep -f "omlx-cli serve"` — works regardless of whether oMLX was started by this script, by Mira's `backend_manager.py`, or manually.
- On `start`, output is appended to `/tmp/omlx.log`.
- On `stop`, sends SIGTERM and polls for exit; falls back to SIGKILL after 10 s.
- `start` times out and returns an error if oMLX is not ready after 60 s.

## Notes

- `~/.local/bin/omlx` is oMLX's own CLI entry point (installed by the app). Do not confuse it with `omlx-ctl`.
- The model directory must match `mira.yaml` exactly: `~/.omlx/models/Qwen3.6-35B-A3B/`.
- oMLX also starts automatically when Mira starts (via `backend_manager.ensure_backend_running()`), so manual `omlx-ctl start` is usually only needed for standalone testing.
