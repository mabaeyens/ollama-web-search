"""FastAPI server for the ollama Search Tool web interface."""

import asyncio
import json
import logging
import threading
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from config import VERBOSE_DEFAULT
from orchestrator import ChatOrchestrator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

orchestrator: ChatOrchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global orchestrator
    orchestrator = ChatOrchestrator(verbose=VERBOSE_DEFAULT)
    logger.info(f"Initialized orchestrator with model: {orchestrator.model}")
    yield


app = FastAPI(title="ollama Search Tool", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str


class VerboseRequest(BaseModel):
    enabled: bool


@app.get("/")
async def index():
    return FileResponse("static/index.html")


@app.post("/chat")
async def chat(request: ChatRequest):
    """SSE endpoint — streams typed events from stream_chat() to the browser."""
    async def event_stream():
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        def produce():
            try:
                for event in orchestrator.stream_chat(request.message):
                    loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception as e:
                loop.call_soon_threadsafe(
                    queue.put_nowait, {"type": "error", "message": str(e)}
                )
            finally:
                loop.call_soon_threadsafe(queue.put_nowait, None)

        threading.Thread(target=produce, daemon=True).start()

        while True:
            event = await queue.get()
            if event is None:
                break
            yield {"data": json.dumps(event)}

    return EventSourceResponse(event_stream())


@app.post("/reset")
async def reset():
    orchestrator.reset_conversation()
    return {"status": "ok"}


@app.post("/verbose")
async def set_verbose(request: VerboseRequest):
    orchestrator.verbose = request.enabled
    return {"verbose": orchestrator.verbose}


@app.get("/status")
async def status():
    return {
        "model": orchestrator.model,
        "verbose": orchestrator.verbose,
        "history_length": len(orchestrator.conversation_history),
    }


if __name__ == "__main__":
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
