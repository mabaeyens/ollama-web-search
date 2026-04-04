"""Rich text formatting utilities."""

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from config import ANSWER_PREFIX, SEARCH_PREFIX, ERROR_PREFIX

console = Console()

def print_header(text: str):
    """Print a styled header."""
    console.print(Panel.fit(text, style="bold blue"))

def print_search_status(query: str, status: str = "Searching..."):
    """Print search status with emoji."""
    icon = "⏳" if status == "Searching..." else ("✅" if "found" in status.lower() else "❌")
    console.print(f"{icon} {SEARCH_PREFIX} {status}: {query}")

def print_search_results(results: list):
    """Pretty print search results."""
    if not results:
        console.print("[yellow]⚠️  No search results found.[/yellow]")
        return
    
    table = Table(title="Search Results", show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Title", style="cyan")
    table.add_column("Snippet", style="white")
    table.add_column("URL", style="green", overflow="fold")
    
    for i, r in enumerate(results, 1):
        table.add_row(
            str(i),
            r["title"],
            r["snippet"][:150] + "..." if len(r["snippet"]) > 150 else r["snippet"],
            r["url"]
        )
    
    console.print(table)

def print_answer(text: str):
    """Print the final answer with markdown support."""
    console.print(Markdown(f"{ANSWER_PREFIX}{text}"))

def print_error(message: str):
    """Print an error message."""
    console.print(f"[red]{ERROR_PREFIX}{message}[/red]")

def print_verbose_header():
    """Print verbose mode indicator."""
    console.print("\n[dim]--- VERBOSE MODE: Showing search details ---[/dim]\n")