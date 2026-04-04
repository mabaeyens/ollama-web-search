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
