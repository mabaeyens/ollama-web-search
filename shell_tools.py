"""Shell command execution — cwd always sandboxed to WORKSPACE_ROOT."""

import re
import subprocess
from pathlib import Path
from typing import Any, Dict

from config import SHELL_TIMEOUT
from workspace import safe_path, rel

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


def run_shell(command: str, cwd: str = ".", force: bool = False) -> Dict[str, Any]:
    try:
        work_dir = safe_path(cwd)
    except ValueError as e:
        return {"error": str(e)}

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
