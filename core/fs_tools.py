"""Filesystem tool implementations — all paths sandboxed to WORKSPACE_ROOT."""

import re
import shutil
from pathlib import Path
from typing import Any, Dict

from .workspace import safe_path, rel


def read_file(path: str) -> Dict[str, Any]:
    try:
        p = safe_path(path)
    except ValueError as e:
        return {"error": str(e)}
    if not p.exists():
        return {"error": f"File not found: {path}"}
    if not p.is_file():
        return {"error": f"Not a file: {path}"}
    content = p.read_text(encoding="utf-8", errors="replace")
    return {"path": rel(p), "content": content, "size": len(content)}


def write_file(path: str, content: str) -> Dict[str, Any]:
    try:
        p = safe_path(path)
    except ValueError as e:
        return {"error": str(e)}
    p.parent.mkdir(parents=True, exist_ok=True)
    existed = p.exists()
    p.write_text(content, encoding="utf-8")
    return {
        "path": rel(p),
        "bytes_written": len(content.encode()),
        "action": "updated" if existed else "created",
    }


def list_files(path: str = ".", recursive: bool = False) -> Dict[str, Any]:
    try:
        p = safe_path(path)
    except ValueError as e:
        return {"error": str(e)}
    if not p.exists():
        return {"error": f"Path not found: {path}"}
    if not p.is_dir():
        return {"error": f"Not a directory: {path}"}
    iterator = sorted(p.rglob("*")) if recursive else sorted(p.iterdir())
    entries = []
    for item in iterator:
        if any(part.startswith(".") for part in item.parts[-3:]):
            continue
        entries.append({
            "path": rel(item),
            "type": "dir" if item.is_dir() else "file",
            "size": item.stat().st_size if item.is_file() else None,
        })
    return {"path": rel(p), "entries": entries, "count": len(entries)}


def search_files(pattern: str, path: str = ".", case_sensitive: bool = False) -> Dict[str, Any]:
    try:
        p = safe_path(path)
    except ValueError as e:
        return {"error": str(e)}
    if not p.exists():
        return {"error": f"Path not found: {path}"}
    flags = 0 if case_sensitive else re.IGNORECASE
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        return {"error": f"Invalid pattern: {e}"}
    matches = []
    for file_path in sorted(p.rglob("*")):
        if not file_path.is_file():
            continue
        try:
            for i, line in enumerate(file_path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if regex.search(line):
                    matches.append({"file": rel(file_path), "line": i, "content": line.strip()[:200]})
                    if len(matches) >= 200:
                        return {"matches": matches, "count": len(matches), "truncated": True}
        except Exception:
            continue
    return {"matches": matches, "count": len(matches), "truncated": False}


def move_file(src: str, dst: str) -> Dict[str, Any]:
    try:
        s = safe_path(src)
        d = safe_path(dst)
    except ValueError as e:
        return {"error": str(e)}
    if not s.exists():
        return {"error": f"Source not found: {src}"}
    d.parent.mkdir(parents=True, exist_ok=True)
    s.rename(d)
    return {"from": rel(s), "to": rel(d)}


def delete_file(path: str, confirm: bool = False) -> Dict[str, Any]:
    try:
        p = safe_path(path)
    except ValueError as e:
        return {"error": str(e)}
    if not p.exists():
        return {"error": f"Not found: {path}"}
    r = rel(p)
    if not confirm:
        kind = "directory" if p.is_dir() else "file"
        return {
            "requires_confirmation": True,
            "action": "delete_file",
            "path": r,
            "message": (
                f"This will permanently delete {kind} '{r}'. "
                "Ask the user to confirm, then call delete_file again with confirm=true."
            ),
        }
    if p.is_dir():
        shutil.rmtree(p)
        return {"deleted": r, "type": "directory"}
    p.unlink()
    return {"deleted": r, "type": "file"}
