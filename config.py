"""Configuration settings for the ollama Search Tool."""

import os

# Model settings
MODEL_NAME = "gemma4:26b"
MAX_SEARCH_RESULTS = 5
MAX_TOOL_STEPS = 5   # max tool calls per user turn before giving up
MAX_RETRIES = 3      # API-level error retries per model call

# Search settings
USE_NATIVE_SEARCH = False  # Ollama native search requires a paid subscription; use DuckDuckGo
SEARCH_TIMEOUT = 30

# Display settings
VERBOSE_DEFAULT = False  # Set to True to always show search details
ANSWER_PREFIX = "🤖 "
SEARCH_PREFIX = "🔍 "
ERROR_PREFIX = "❌ "

# Ollama settings
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")