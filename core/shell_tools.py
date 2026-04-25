"""Shell command execution — cwd always sandboxed to WORKSPACE_ROOT."""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict

from .config import SHELL_TIMEOUT, WORKSPACE_ROOT
from .workspace import safe_path, rel

_DANGEROUS = [
    (re.compile(r"\brm\s+.*-[rRf]", re.I),          "rm with -r/-f flag"),
    (re.compile(r"\bgit\s+push\b.*--force", re.I),   "git push --force"),
    (re.compile(r"\bgit\s+reset\s+--hard\b", re.I),  "git reset --hard"),
    (re.compile(r"\bgit\s+clean\s+-[fFdx]", re.I),   "git clean -f/-d/-x"),
    (re.compile(r"\bdd\s+if=", re.I),                "dd disk write"),
    (re.compile(r"\bsudo\b", re.I),                  "sudo"),
    (re.compile(r"\bmkfs\b", re.I),                  "mkfs"),
    (re.compile(r">\s*/dev/", re.I),                 "write to /dev/"),
    (re.compile(r"\bdrop\s+table\b", re.I),          "DROP TABLE"),
]

# Matches absolute paths that are NOT inside WORKSPACE_ROOT.
# Built at import time so the workspace root is baked in.
def _build_abs_path_outside_workspace_pattern() -> re.Pattern:
    ws = str(Path(WORKSPACE_ROOT).expanduser().resolve())
    # Match /something where "something" doesn't start with the workspace path
    # (excluding the workspace prefix itself).  We flag any bare / argument so
    # the model can't escape the sandbox via 'ls /', 'cat /etc/passwd', etc.
    return re.compile(
        r'(?<!\w)/'          # a slash not preceded by a word char (i.e. not part of a flag like -f)
        r'(?!' + re.escape(ws.lstrip('/')) + r'(?:/|$))',  # not the workspace root
    )

_ABS_PATH_OUTSIDE_WS = _build_abs_path_outside_workspace_pattern()


def run_shell(command: str, cwd: str = ".", force: bool = False) -> Dict[str, Any]:
    try:
        work_dir = safe_path(cwd)
    except ValueError as e:
        return {"error": str(e)}

    # Reject commands that reference absolute paths outside the workspace.
    # This closes the gap where cwd is sandboxed but the command itself could
    # still read/write arbitrary paths (e.g. `ls /`, `cat /etc/passwd`).
    if _ABS_PATH_OUTSIDE_WS.search(command):
        return {
            "error": (
                "Command references an absolute path outside the workspace. "
                "Use relative paths only (e.g. '.' or 'subdir/file'). "
                f"Workspace root: {WORKSPACE_ROOT}"
            )
        }

    for pattern, label in _DANGEROUS:
        if pattern.search(command):
            if not force:
                return {
                    "requires_confirmation": True,
                    "action": "run_shell",
                    "command": command,
                    "matched": label,
                    "message": (
                        f"Command contains a potentially destructive operation ({label}). "
                        "Ask the user to confirm, then call run_shell again with force=true."
                    ),
                }
            break  # user confirmed — allow it

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT,
        )
        return {
            "command": command,
            "cwd": rel(work_dir),
            "exit_code": result.returncode,
            "stdout": result.stdout[:8000],
            "stderr": result.stderr[:2000],
            "truncated": len(result.stdout) > 8000 or len(result.stderr) > 2000,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timed out after {SHELL_TIMEOUT}s", "command": command}
    except Exception as e:
        return {"error": str(e), "command": command}
