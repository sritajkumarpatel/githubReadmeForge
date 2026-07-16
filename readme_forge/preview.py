import os
import sys
import http.server
import socketserver
import webbrowser
from pathlib import Path
from threading import Thread
from rich.console import Console
from rich.markdown import Markdown

class PreviewHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP handler to serve the showroom.html file as index."""
    def __init__(self, *args, directory=None, showroom_name="showroom.html", **kwargs):
        self.showroom_name = showroom_name
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        # Redirect index requests to the showroom file
        if self.path == "/" or self.path == "/index.html":
            self.path = f"/{self.showroom_name}"
        return super().do_GET()


class Previewer:
    def __init__(self, readme_path, showroom_path):
        self.readme_path = Path(readme_path)
        self.showroom_path = Path(showroom_path)
        self.console = Console()

    def show_in_terminal(self):
        """Displays the generated markdown in the terminal using Rich's Markdown parser."""
        if not self.readme_path.exists():
            self.console.print(f"[red]Error: README.md not found at {self.readme_path}[/red]")
            return

        self.console.print("\n[bold blue]--- Markdown Terminal Preview ---[/bold blue]\n")
        markdown_text = self.readme_path.read_text(encoding="utf-8")
        # Parse and print
        r_markdown = Markdown(markdown_text)
        self.console.print(r_markdown)
        self.console.print("\n[bold blue]--------------------------------[/bold blue]\n")

    def launch_showroom_server(self, port=8080):
        """Starts a local HTTP server in a separate thread and opens the default browser to preview the showroom."""
        if not self.showroom_path.exists():
            self.console.print(f"[red]Error: Showroom HTML file not found at {self.showroom_path}[/red]")
            return

        directory = str(self.showroom_path.parent)
        file_name = self.showroom_path.name

        # Create custom handler factor to bind specific directory and file
        def handler_factory(*args, **kwargs):
            return PreviewHandler(*args, directory=directory, showroom_name=file_name, **kwargs)

        socketserver.TCPServer.allow_reuse_address = True
        try:
            server = socketserver.TCPServer(("", port), handler_factory)
        except OSError:
            # If port is in use, try port + 1
            port += 1
            try:
                server = socketserver.TCPServer(("", port), handler_factory)
            except OSError as e:
                self.console.print(f"[red]Failed to start local preview server: {e}[/red]")
                return

        server_url = f"http://localhost:{port}"
        self.console.print(f"\n[bold green]🌐 Showroom Preview Server launched![/bold green]")
        self.console.print(f"Opening showroom website at: [cyan]{server_url}[/cyan]")
        self.console.print("[yellow]Press Ctrl+C in this terminal to stop the preview server.[/yellow]\n")

        # Open webbrowser in a delayed daemon thread or directly
        def open_browser():
            import time
            time.sleep(1)
            webbrowser.open(server_url)

        browser_thread = Thread(target=open_browser, daemon=True)
        browser_thread.start()

        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Stopping local preview server...[/yellow]")
            server.shutdown()
            server.server_close()
            self.console.print("[green]Preview server stopped.[/green]")
