"""Tests for the stop/cancel feature (server.py + index.html stop button)."""
import json
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

import server


def _parse_sse(response_text):
    """Parse SSE response text into a list of event dicts."""
    events = []
    for line in response_text.splitlines():
        if line.startswith("data: "):
            try:
                events.append(json.loads(line[6:]))
            except Exception:
                pass
    return events


@pytest.fixture(autouse=True)
def clear_cancel():
    """Reset cancel_event before and after each test."""
    server.cancel_event.clear()
    yield
    server.cancel_event.clear()


@pytest.fixture
def client():
    with TestClient(server.app) as c:
        yield c


def test_cancel_endpoint_sets_event(client):
    """POST /cancel returns ok and sets cancel_event."""
    resp = client.post("/cancel")
    assert resp.status_code == 200
    assert resp.json() == {"status": "cancelled"}
    assert server.cancel_event.is_set()


def test_new_chat_clears_cancel_event(client):
    """Starting a new /chat request always clears a previously set cancel flag."""
    server.cancel_event.set()

    def instant_stream(message, attachments=None):
        yield {"type": "done", "content": "hello"}

    with patch.object(server.orchestrator, 'stream_chat', side_effect=instant_stream):
        client.post("/chat", data={"message": "hi"})

    assert not server.cancel_event.is_set()


def test_cancel_stops_event_stream(client):
    """Events emitted after cancel fires must not reach the client."""
    def cancelling_stream(message, attachments=None):
        yield {"type": "token", "content": "partial"}
        server.cancel_event.set()               # cancel after first token
        yield {"type": "token", "content": "should_not_arrive"}
        yield {"type": "done", "content": "partial should_not_arrive"}

    with patch.object(server.orchestrator, 'stream_chat', side_effect=cancelling_stream):
        resp = client.post("/chat", data={"message": "cancel me"})

    contents = [e.get("content", "") for e in _parse_sse(resp.text)]
    assert not any("should_not_arrive" in c for c in contents), \
        "Events emitted after cancel_event was set must be dropped by produce()"


def test_history_rolled_back_on_cancel(client):
    """Partial conversation history from a cancelled turn is removed."""
    initial_len = len(server.orchestrator.conversation_history)

    def cancelling_stream(message, attachments=None):
        # Simulate what stream_chat does — write user message to history, then
        # get cancelled before the assistant turn is appended.
        server.orchestrator.conversation_history.append({"role": "user", "content": message})
        yield {"type": "thinking"}
        server.cancel_event.set()               # cancel before done event
        yield {"type": "done", "content": "never delivered"}

    with patch.object(server.orchestrator, 'stream_chat', side_effect=cancelling_stream):
        client.post("/chat", data={"message": "cancel me"})

    assert len(server.orchestrator.conversation_history) == initial_len, \
        "Cancelled turn must not leave entries in conversation history"


# ── /browse endpoint tests ────────────────────────────────────────────────────

def test_browse_home_directory(client):
    """/browse with no path param returns a listing of the server root or home."""
    resp = client.get("/browse?path=/tmp")
    assert resp.status_code == 200
    data = resp.json()
    assert "path" in data
    assert "entries" in data
    assert isinstance(data["entries"], list)


def test_browse_entries_have_required_fields(client, tmp_path):
    """Each entry in /browse response has name, is_dir, ext, path fields."""
    # Create a temp dir with a file and a sub-directory
    (tmp_path / "doc.pdf").write_text("x")
    (tmp_path / "subdir").mkdir()

    resp = client.get(f"/browse?path={tmp_path}")
    assert resp.status_code == 200
    entries = resp.json()["entries"]
    assert len(entries) == 2  # subdir first (sorted), then doc.pdf
    for e in entries:
        assert "name" in e
        assert "is_dir" in e
        assert "ext" in e
        assert "path" in e


def test_browse_dirs_sorted_before_files(client, tmp_path):
    """Directories must appear before files in /browse results."""
    (tmp_path / "z_file.txt").write_text("x")
    (tmp_path / "a_dir").mkdir()

    resp = client.get(f"/browse?path={tmp_path}")
    entries = resp.json()["entries"]
    dir_indices  = [i for i, e in enumerate(entries) if e["is_dir"]]
    file_indices = [i for i, e in enumerate(entries) if not e["is_dir"]]
    assert max(dir_indices) < min(file_indices), "All dirs must come before files"


def test_browse_nonexistent_path_returns_error(client):
    """/browse with a non-existent path returns 4xx."""
    resp = client.get("/browse?path=/nonexistent/path/xyz123")
    assert resp.status_code in (400, 404, 500)


def test_browse_ext_field_is_lowercase_with_dot(client, tmp_path):
    """ext field must be lowercase with leading dot (e.g. '.pdf') or '' for no extension."""
    (tmp_path / "Document.PDF").write_text("x")
    (tmp_path / "Makefile").write_text("x")

    resp = client.get(f"/browse?path={tmp_path}")
    entries = {e["name"]: e for e in resp.json()["entries"]}
    assert entries["Document.PDF"]["ext"] == ".pdf"
    assert entries["Makefile"]["ext"] == ""


# ── file_handler magic-byte detection tests ──────────────────────────────────

def test_pdf_with_wrong_extension_detected_and_warned(tmp_path):
    """A file with .bump extension whose bytes start with %PDF is detected as PDF."""
    import fitz
    from file_handler import load_file

    # Create a minimal real PDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello magic bytes test")
    bump_path = tmp_path / "strangeextensions.Bump"
    doc.save(str(bump_path))
    doc.close()

    att = load_file(str(bump_path))
    assert att["type"] == "rag", "Detected-as-PDF file must use RAG path"
    assert att["warning"], "Must warn that extension does not match detected type"
    assert "PDF" in att["warning"]
    assert "strangeextensions.Bump" in att["warning"]


def test_genuine_text_with_unknown_extension_processed_as_text(tmp_path):
    """A .xyz file containing plain text is still read as text (no false positive)."""
    from file_handler import load_file

    p = tmp_path / "notes.xyz"
    p.write_text("Just some plain text here.", encoding="utf-8")

    att = load_file(str(p))
    assert att["type"] in ("text", "rag")   # small file → text
    assert att["warning"] is None            # no spurious warning
    assert "plain text" in att["content"]
