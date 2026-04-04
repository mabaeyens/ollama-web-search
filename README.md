# ollama Search Tool

A local AI assistant powered by **Gemma 4:26b** and **Ollama** with autonomous web search capabilities.

## Features

- **Autonomous Search**: Model decides when to search based on query type
- **Dual Search Engines**: Ollama native search with DuckDuckGo fallback
- **Clean CLI**: Rich-formatted output with toggleable verbosity
- **Private**: Runs entirely on your local machine

## Prerequisites

- **Python 3.12+**
- **Ollama** (v0.20.2+)
- **uv**
- **Gemma 4:26b** model pulled: `ollama pull gemma4:26b`

## Setup

```bash
uv venv --python 3.12
source .venv/bin/activate
uv sync
```

## Running

```bash
uv run python main.py
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/toggle` | Toggle verbose mode (show/hide search details) |
| `/verbose` | Enable verbose mode |
| `/quiet` | Disable verbose mode |
| `/reset` | Reset conversation history |
| `/quit` | Exit |

## Testing

All model and search calls are mocked — no Ollama instance needed to run tests.

```bash
uv run pytest                                              # all tests
uv run pytest tests/test_queries.py::test_toggle_verbose  # single test
```

## Configuration

All settings are in `config.py`:

| Setting | Default | Description |
|---------|---------|-------------|
| `MODEL_NAME` | `gemma4:26b` | Ollama model |
| `USE_NATIVE_SEARCH` | `True` | Try Ollama native search first |
| `MAX_SEARCH_RESULTS` | `5` | Results per search |
| `MAX_TOOL_STEPS` | `5` | Max tool calls per turn |
| `MAX_RETRIES` | `3` | API error retries per call |
| `SEARCH_TIMEOUT` | `30` | DuckDuckGo timeout in seconds |
| `VERBOSE_DEFAULT` | `False` | Start in verbose mode |
| `OLLAMA_HOST` | `http://localhost:11434` | Override via `OLLAMA_HOST` env var |
