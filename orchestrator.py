"""Core orchestration logic for tool calling and search."""

import logging
from typing import List, Dict, Optional

import ollama
from config import MODEL_NAME, MAX_RETRIES, MAX_TOOL_STEPS, VERBOSE_DEFAULT
from tools import TOOLS
from prompts import SYSTEM_PROMPT, SEARCH_RESULT_TEMPLATE
from search_engine import SearchEngine
from formatter import (
    console, print_header, print_search_status, print_search_results,
    print_answer, print_error, print_verbose_header
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
        
        # Initialize conversation with system prompt
        self._add_system_prompt()
    
    def _add_system_prompt(self):
        """Add system prompt to conversation history."""
        if not self.system_prompt_added:
            self.conversation_history.append({
                "role": "system",
                "content": SYSTEM_PROMPT
            })
            self.system_prompt_added = True
    
    def chat(self, user_message: str) -> str:
        """
        Process a user message, potentially triggering search, and return the final answer.
        
        Args:
            user_message: The user's input
            
        Returns:
            The final answer string
        """
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })
        
        # Outer loop: one iteration per tool call step; exits on final answer or step limit
        for step in range(MAX_TOOL_STEPS):
            response = self._call_model_with_retry(self.conversation_history, tools=TOOLS)

            if not (hasattr(response, 'tool_calls') and response.tool_calls):
                # No tool call — this is the final answer
                final_answer = response.message.content
                self.conversation_history.append({"role": "assistant", "content": final_answer})

                if self.verbose:
                    console.print("\n[dim]--- FINAL ANSWER ---[/dim]\n")

                print_answer(final_answer)
                return final_answer

            # Model requested a tool call
            tool_call = response.tool_calls[0]
            self.conversation_history.append(response.message)

            if self.verbose:
                print_verbose_header()

            if tool_call.function.name == "web_search":
                query = tool_call.function.arguments.get("query", "")
                num_results = tool_call.function.arguments.get("num_results", 5)

                if self.verbose:
                    print_search_status(query, "Searching...")

                results = self.search_engine.search(query, max_results=num_results)

                if self.verbose:
                    if results:
                        print_search_status(query, f"Found {len(results)} results")
                        print_search_results(results)
                    else:
                        print_search_status(query, "No results found")

                search_summary = self.search_engine.get_search_summary(results)
                search_content = SEARCH_RESULT_TEMPLATE.format(
                    query=query,
                    results_text=search_summary
                )
                self.conversation_history.append({
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": search_content
                })
            else:
                logger.warning(f"Unknown tool called: {tool_call.function.name}")
                self.conversation_history.append({
                    "role": "tool",
                    "name": tool_call.function.name,
                    "content": f"Error: Unknown tool {tool_call.function.name}"
                })

        error_msg = f"Reached {MAX_TOOL_STEPS} tool calls without a final answer."
        logger.error(error_msg)
        print_error(error_msg)
        return "I was unable to produce an answer within the allowed number of steps."
    
    def _call_model_with_retry(self, messages: List[Dict], tools: Optional[List] = None):
        """Call the Ollama model, retrying up to MAX_RETRIES times on API errors."""
        last_exc = None
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._call_model(messages, tools)
            except Exception as e:
                last_exc = e
                logger.warning(f"Ollama API error (attempt {attempt}/{MAX_RETRIES}): {e}")
        raise last_exc

    def _call_model(self, messages: List[Dict], tools: Optional[List] = None):
        """Call the Ollama model (single attempt)."""
        return ollama.chat(
            model=self.model,
            messages=messages,
            tools=tools
        )
    
    def toggle_verbose(self):
        """Toggle verbose mode."""
        self.verbose = not self.verbose
        status = "enabled" if self.verbose else "disabled"
        print(f"Verbose mode {status}.")
        return self.verbose
    
    def reset_conversation(self):
        """Reset conversation history."""
        self.conversation_history = []
        self._add_system_prompt()
        print("Conversation reset.")