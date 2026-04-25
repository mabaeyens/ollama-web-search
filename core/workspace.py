"""Sandbox path enforcement — all filesystem operations go through here."""

from pathlib import Path
from typing import Optional
from .config import WORKSPACE_ROOT


def safe_path(user_path: str, root: Optional[str] = None) -> Path:
    """Resolve path and verify it sits within root (defaults to WORKSPACE_ROOT)."""
    r = Path(root or WORKSPACE_ROOT).expanduser().resolve()
    resolved = (r / user_path).resolve()
    if not str(resolved).startswith(str(r) + "/") and resolved != r:
        raise ValueError(f"Path '{user_path}' is outside the workspace ({r})")
    return resolved


def rel(path: Path, root: Optional[str] = None) -> str:
    """Return a path relative to root (defaults to WORKSPACE_ROOT) as a string."""
    r = Path(root or WORKSPACE_ROOT).expanduser().resolve()
    try:
        return str(path.resolve().relative_to(r))
    except ValueError:
        return str(path)
