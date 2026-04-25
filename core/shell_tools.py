"""Shell command execution — cwd always sandboxed to the active workspace root."""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict, Optional

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


def _abs_outside_ws_pattern(workspace_root: str) -> re.Pattern:
    ws = str(Path(workspace_root).expanduser().resolve())
    return re.compile(
        r'(?<!\w)/'
        r'(?!' + re.escape(ws.lstrip('/')) + r'(?:/|$))',
    )


def run_shell(command: str, cwd: str = ".", force: bool = False, root: Optional[str] = None) -> Dict[str, Any]:
    effective_root = root or WORKSPACE_ROOT
    try:
        work_dir = safe_path(cwd, effective_root)
    except ValueError as e:
        return {"error": str(e)}

    if _abs_outside_ws_pattern(effective_root).search(command):
        return {
            "error": (
                "Command references an absolute path outside the workspace. "
                "Use relative paths only (e.g. '.' or 'subdir/file'). "
                f"Workspace root: {effective_root}"
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
            "cwd": rel(work_dir, effective_root),
            "exit_code": result.returncode,
            "stdout": result.stdout[:8000],
            "stderr": result.stderr[:2000],
            "truncated": len(result.stdout) > 8000 or len(result.stderr) > 2000,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Timed out after {SHELL_TIMEOUT}s", "command": command}
    except Exception as e:
        return {"error": str(e), "command": command}
