"""Core orchestration logic for tool calling and search."""

import sys
import logging
from typing import List, Dict, Optional, Tuple

import ollama
from config import MODEL_NAME, MAX_RETRIES, MAX_TOOL_STEPS, VERBOSE_DEFAULT, ANSWER_PREFIX
from tools import TOOLS
from prompts import build_system_prompt, SEARCH_RESULT_TEMPLATE
from search_engine import SearchEngine
from formatter import (
    console, print_header, print_search_status, print_search_results,
    print_error, print_rule
)

logger = logging.getLogger(__name__)


class ChatOrchestrator:
    """Manages the conversation loop with tool calling."""

    def __init__(self, model: str = MODEL_NAME, verbose: bool = VERBOSE_DEFAULT):
        self.model = model
        self.verbose = verbose
        self.search_engine = SearchEngine()
        self.conversation_history: List[Dict] = []
        self.system_prompt_added = False
        self._add_system_prompt()

    def _add_system_prompt(self):
        if not self.system_prompt_added:
            self.conversation_history.append({
                "role": "system",
                "content": build_system_prompt()
            })
            self.system_prompt_added = True

    def chat(self, user_message: str) -> str:
        """Process a user message, potentially triggering search, and return the final answer."""
        self.conversation_history.append({"role": "user", "content": user_message})

        for step in range(MAX_TOOL_STEPS):
            content, message = self._stream_model_with_retry(self.conversation_history, tools=TOOLS)
            tool_calls = message.tool_calls

            if not tool_calls:
                # Final answer was already streamed to stdout
                self.conversation_history.append({"role": "assistant", "content": content})
                print_rule()
                return content

            # Model requested a tool call
            self.conversation_history.append(message)

            if tool_calls[0].function.name == "web_search":
                tool_call = tool_calls[0]
                query = tool_call.function.arguments.get("query", "")
                num_results = tool_call.function.arguments.get("num_results", 5)

                with console.status(f"[dim]Searching: {query}[/dim]", spinner="dots"):
                    results = self.search_engine.search(query, max_results=num_results)

                if results:
                    print_search_status(query, f"Found {len(results)} results")
                    if self.verbose:
                        print_search_results(results)
                else:
                    print_search_status(query, "No results found")

                search_content = SEARCH_RESULT_TEMPLATE.format(
                    query=query,
                    results_text=self.search_engine.get_search_summary(results)
                )
                self.conversation_history.append({
                    "role": "tool",
                    "name": tool_calls[0].function.name,
                    "content": search_content
                })
            else:
                logger.warning(f"Unknown tool called: {tool_calls[0].function.name}")
                self.conversation_history.append({
                    "role": "tool",
                    "name": tool_calls[0].function.name,
                    "content": f"Error: Unknown tool {tool_calls[0].function.name}"
                })

        error_msg = f"Reached {MAX_TOOL_STEPS} tool calls without a final answer."
        logger.error(error_msg)
        print_error(error_msg)
        return "I was unable to produce an answer within the allowed number of steps."

    def _stream_model_with_retry(self, messages: List[Dict], tools: Optional[List] = None) -> Tuple[str, object]:
        """Stream the model response, retrying up to MAX_RETRIES times on API errors."""
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._stream_model(messages, tools)
            except Exception as e:
                last_exc = e
                logger.warning(f"Ollama API error (attempt {attempt}/{MAX_RETRIES}): {e}")
        raise last_exc

    def _stream_model(self, messages: List[Dict], tools: Optional[List] = None) -> Tuple[str, object]:
        """
        Stream a model response.

        Shows a spinner until the first content token arrives, then streams
        tokens directly to stdout. Tool-call responses (empty content) only
        show the spinner with no visible output.

        Returns (full_content, final_message).
        """
        full_content = ""
        final_message = None
        started_streaming = False

        status = console.status("[dim]Thinking…[/dim]", spinner="dots")
        status.start()

        try:
            for chunk in ollama.chat(
                model=self.model,
                messages=messages,
                tools=tools,
                stream=True
            ):
                token = chunk.message.content or ""

                if token and not started_streaming:
                    status.stop()
                    sys.stdout.write(f"\n{ANSWER_PREFIX}")
                    sys.stdout.flush()
                    started_streaming = True

                if token:
                    sys.stdout.write(token)
                    sys.stdout.flush()
                    full_content += token

                if chunk.done:
                    final_message = chunk.message

        except Exception:
            status.stop()
            raise

        if not started_streaming:
            status.stop()

        if started_streaming:
            sys.stdout.write("\n")
            sys.stdout.flush()

        final_message.content = full_content
        return full_content, final_message

    def toggle_verbose(self):
        """Toggle verbose mode."""
        self.verbose = not self.verbose
        status = "enabled" if self.verbose else "disabled"
        print(f"Verbose mode {status}.")
        return self.verbose

    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        self.system_prompt_added = False
        self._add_system_prompt()
        print("Conversation reset.")
