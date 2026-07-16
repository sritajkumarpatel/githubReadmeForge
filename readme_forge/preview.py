import os
import sys
from pathlib import Path
from rich.console import Console
from rich.markdown import Markdown

class Previewer:
    def __init__(self, readme_path):
        self.readme_path = Path(readme_path)
        self.console = Console()

    def show_in_terminal(self):
        """Displays the generated markdown in the terminal using Rich's Markdown parser."""
        if not self.readme_path.exists():
            self.console.print(f"[red]Error: README.md not found at {self.readme_path}[/red]")
            return

        self.console.print("\n[bold blue]--- Markdown Terminal Preview ---[/bold blue]\n")
        markdown_text = self.readme_path.read_text(encoding="utf-8")
        r_markdown = Markdown(markdown_text)
        self.console.print(r_markdown)
        self.console.print("\n[bold blue]--------------------------------[/bold blue]\n")
