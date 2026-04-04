#!/usr/bin/env python3
"""Main CLI entry point for ollama Search Tool."""

import sys
import logging
from config import VERBOSE_DEFAULT
from orchestrator import ChatOrchestrator
from formatter import print_header, print_error

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    """Main entry point."""
    print_header("🤖 ollama Search Tool (Gemma 4 + Ollama)")
    print("Type your message. Use /help for commands, /quit to exit.\n")
    
    # Initialize orchestrator
    verbose = VERBOSE_DEFAULT
    orchestrator = ChatOrchestrator(verbose=verbose)
    
    # Main chat loop
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                
                if cmd == "/quit" or cmd == "/exit":
                    print("Goodbye!")
                    break
                
                elif cmd == "/help":
                    print("""
Available commands:
  /help      - Show this help message
  /quit      - Exit the program
  /toggle    - Toggle verbose mode (show/hide search details)
  /reset     - Reset conversation history
  /verbose   - Enable verbose mode
  /quiet     - Disable verbose mode
                    """)
                    continue
                
                elif cmd == "/toggle":
                    orchestrator.toggle_verbose()
                    continue
                
                elif cmd == "/verbose":
                    orchestrator.verbose = True
                    print("Verbose mode enabled.")
                    continue
                
                elif cmd == "/quiet":
                    orchestrator.verbose = False
                    print("Verbose mode disabled.")
                    continue
                
                elif cmd == "/reset":
                    orchestrator.reset_conversation()
                    continue
                
                else:
                    print(f"Unknown command: {cmd}. Type /help for options.")
                    continue
            
            # Process user message
            orchestrator.chat(user_input)
            print()  # Empty line for readability
            
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            continue

if __name__ == "__main__":
    main()