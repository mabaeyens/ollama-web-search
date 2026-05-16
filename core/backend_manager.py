"""Manages start/stop of inference server processes for runtime backend switching."""

import logging
import subprocess
import time
import urllib.request

logger = logging.getLogger(__name__)

OMLX_CLI = "/Applications/oMLX.app/Contents/MacOS/omlx-cli"
OMLX_PORT = 8080
OMLX_HOST = f"http://localhost:{OMLX_PORT}"
OMLX_MODEL = "Qwen3.6-35B-A3B"
OMLX_CONTEXT = 262144

OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:26b"
OLLAMA_CONTEXT = 65536

PRESETS = {
    "omlx": {
        "backend": "omlx",
        "model": OMLX_MODEL,
        "host": OMLX_HOST,
        "embed_backend": "omlx",
        "embed_host": OMLX_HOST,
        "context_window": OMLX_CONTEXT,
    },
    "ollama": {
        "backend": "ollama",
        "model": OLLAMA_MODEL,
        "host": OLLAMA_HOST,
        "embed_backend": "ollama",
        "embed_host": OLLAMA_HOST,
        "context_window": OLLAMA_CONTEXT,
    },
}

_omlx_proc = None


def _wait_for_ready(url: str, timeout: int = 60) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return
        except Exception:
            time.sleep(1)
    raise TimeoutError(f"Server did not become ready at {url} after {timeout}s")


def stop_ollama() -> None:
    subprocess.run(["osascript", "-e", 'quit app "Ollama"'], capture_output=True)
    time.sleep(2)


def start_ollama() -> None:
    subprocess.run(["open", "-a", "Ollama"])
    _wait_for_ready(OLLAMA_HOST + "/api/version", timeout=30)


def stop_omlx() -> None:
    global _omlx_proc
    if _omlx_proc and _omlx_proc.poll() is None:
        _omlx_proc.terminate()
        try:
            _omlx_proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            _omlx_proc.kill()
        _omlx_proc = None


def start_omlx() -> None:
    global _omlx_proc
    _omlx_proc = subprocess.Popen(
        [OMLX_CLI, "serve", "--port", str(OMLX_PORT)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    _wait_for_ready(OMLX_HOST + "/v1/models", timeout=60)


def switch_to(target: str) -> dict:
    """Stop the running inference server and start the target one.

    Returns the preset config dict; caller is responsible for updating the
    orchestrator and the server's runtime state.

    Raises ValueError for unknown backends, TimeoutError if the new server
    does not respond within its startup window.
    """
    if target not in PRESETS:
        raise ValueError(f"Unknown backend {target!r}. Must be 'ollama' or 'omlx'.")
    logger.info("Switching backend to %s", target)
    if target == "omlx":
        stop_ollama()
        start_omlx()
    else:
        stop_omlx()
        start_ollama()
    logger.info("Backend switch to %s complete", target)
    return PRESETS[target]
