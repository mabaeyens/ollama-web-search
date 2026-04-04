# ollama Search Tool

A local AI assistant powered by **Gemma 4:26b** and **Ollama** with autonomous web search. Available as a CLI tool and a local web interface with streaming markdown responses.

## Features

- **Autonomous Search**: Model decides when to search based on query type (ReAct pattern)
- **Streaming responses**: Tokens appear live; markdown rendered as you read
- **Two interfaces**: Rich CLI and local web UI (FastAPI + SSE)
- **Private**: Runs entirely on your local machine — no cloud APIs, no API keys

## Prerequisites

- **Python 3.12+**
- **Ollama** (v0.20.2+) running locally
- **uv** package manager
- **Gemma 4:26b** model: `ollama pull gemma4:26b`

## Setup

```bash
uv venv --python 3.12
source .venv/bin/activate
uv sync
```

## Running

**CLI:**
```bash
python main.py
```

**Web interface** — open `http://localhost:8000` in your browser:
```bash
python server.py
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

## Web Interface

The web UI supports the same features as the CLI:
- Streaming responses with live markdown rendering
- Search status chips (searching → found N results)
- Verbose toggle and conversation reset in the header
- Enter to send, Shift+Enter for newline

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
| `USE_NATIVE_SEARCH` | `False` | Disabled — requires paid Ollama subscription |
| `MAX_SEARCH_RESULTS` | `5` | Results per search |
| `MAX_TOOL_STEPS` | `5` | Max tool calls per turn |
| `MAX_RETRIES` | `3` | API error retries per call |
| `SEARCH_TIMEOUT` | `30` | DuckDuckGo timeout in seconds |
| `VERBOSE_DEFAULT` | `False` | Start in verbose mode |
| `OLLAMA_HOST` | `http://localhost:11434` | Override via `OLLAMA_HOST` env var |

## Roadmap

### File Attachments (next)
- **Images**: Gemma 4 is natively multimodal — pass image bytes directly to Ollama
- **Text / code files**: Extract content and inject into conversation context
- **Large PDFs**: RAG — chunk, embed (`sentence-transformers`), store (ChromaDB), retrieve relevant sections per query
