"""Tests for the ollama Search Tool."""

import pytest
from unittest.mock import MagicMock, patch
from orchestrator import ChatOrchestrator


# --- Mock factories ---

def _tool_call_response(query="test"):
    """Mock model response that requests a web_search tool call."""
    tool_call = MagicMock()
    tool_call.function.name = "web_search"
    tool_call.function.arguments = {"query": query, "num_results": 5}
    response = MagicMock()
    response.message.tool_calls = [tool_call]
    response.message.content = ""
    return response


def _final_response(content="Answer."):
    """Mock model response with a final answer and no tool calls."""
    response = MagicMock()
    response.message.tool_calls = None
    response.message.content = content
    return response


FAKE_SEARCH_RESULTS = [
    {"title": "Test Result", "url": "http://example.com", "snippet": "Some content."}
]


# --- Fixtures ---

@pytest.fixture
def orchestrator():
    return ChatOrchestrator(verbose=False)


# --- Tests ---

def test_historical_fact_no_search(orchestrator):
    """Historical facts should be answered without triggering a search."""
    with patch.object(orchestrator, '_call_model', return_value=_final_response("William Shakespeare wrote Hamlet.")), \
         patch.object(orchestrator.search_engine, 'search') as mock_search:
        response = orchestrator.chat("Who wrote Hamlet?")
        mock_search.assert_not_called()
        assert len(response) > 0


def test_current_event_triggers_search(orchestrator):
    """Events after the knowledge cutoff should trigger a web search."""
    with patch.object(orchestrator, '_call_model', side_effect=[
        _tool_call_response("2026 Super Bowl"),
        _final_response("The Eagles won the 2026 Super Bowl."),
    ]), patch.object(orchestrator.search_engine, 'search', return_value=FAKE_SEARCH_RESULTS) as mock_search:
        response = orchestrator.chat("What happened in the 2026 Super Bowl?")
        mock_search.assert_called_once()
        assert len(response) > 0


def test_weather_query_triggers_search(orchestrator):
    """Time-sensitive queries should trigger a web search."""
    with patch.object(orchestrator, '_call_model', side_effect=[
        _tool_call_response("weather today"),
        _final_response("It is sunny today."),
    ]), patch.object(orchestrator.search_engine, 'search', return_value=FAKE_SEARCH_RESULTS) as mock_search:
        response = orchestrator.chat("What's the weather like today?")
        mock_search.assert_called_once()
        assert len(response) > 0


def test_general_knowledge_no_search(orchestrator):
    """General knowledge questions should not trigger a search."""
    with patch.object(orchestrator, '_call_model', return_value=_final_response("Photosynthesis is the process...")), \
         patch.object(orchestrator.search_engine, 'search') as mock_search:
        response = orchestrator.chat("Explain what photosynthesis is")
        mock_search.assert_not_called()
        assert len(response) > 0


def test_toggle_verbose(orchestrator):
    """Verbose toggle should flip the flag each call."""
    assert orchestrator.verbose is False
    orchestrator.toggle_verbose()
    assert orchestrator.verbose is True
    orchestrator.toggle_verbose()
    assert orchestrator.verbose is False


def test_reset_conversation(orchestrator):
    """Reset should restore conversation history to system prompt only."""
    orchestrator.conversation_history.append({"role": "user", "content": "test"})
    orchestrator.conversation_history.append({"role": "assistant", "content": "test"})
    orchestrator.reset_conversation()
    assert len(orchestrator.conversation_history) == 1
    assert orchestrator.conversation_history[0]["role"] == "system"
