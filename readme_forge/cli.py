import argparse
import sys
import os
from pathlib import Path
from rich.console import Console

from readme_forge.agents.orchestrator import Orchestrator
from readme_forge.preview import Previewer

def parse_args():
    parser = argparse.ArgumentParser(
        description="🛠️ githubReadmeForge: Multi-agent CLI to craft beautiful visual READMEs."
    )
    parser.add_argument(
        "--path", "-p",
        default=".",
        help="Local repository path or HTTP/Git URL of a remote repository."
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "claude", "ollama", "mock"],
        help="LLM provider (defaults to 'gemini' if GEMINI_API_KEY exists, else 'mock')."
    )
    parser.add_argument(
        "--model",
        help="Model name (e.g., 'gemini-1.5-flash', 'gpt-4o-mini', 'llama3')."
    )
    parser.add_argument(
        "--instant", "-i",
        action="store_true",
        help="Run instantly without interactive questions."
    )
    parser.add_argument(
        "--preview", "-v",
        action="store_true",
        help="Directly preview existing README.md and showroom.html in the specified target path."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port to host the local showroom preview server (default: 8080)."
    )

    return parser.parse_args()


def main():
    args = parse_args()
    console = Console()

    # If user wants to directly preview files in path
    if args.preview:
        target_dir = Path(args.path).resolve()
        readme_path = target_dir / "README.md"
        showroom_path = target_dir / "showroom.html"

        if not readme_path.exists() and not showroom_path.exists():
            # Check for alternative README_new.md
            readme_path = target_dir / "README_new.md"
            if not readme_path.exists():
                console.print(f"[red]Error: No README.md or showroom.html found at {target_dir}[/red]")
                sys.exit(1)

        previewer = Previewer(readme_path, showroom_path)
        # Show rendered markdown in terminal
        previewer.show_in_terminal()
        # Launch browser server if showroom exists
        if showroom_path.exists():
            previewer.launch_showroom_server(port=args.port)
        else:
            console.print("[yellow]Showroom HTML file does not exist, skipping local web preview.[/yellow]")
        return

    # Auto-resolve provider if not specified
    provider = args.provider
    if not provider:
        if os.getenv("GEMINI_API_KEY"):
            provider = "gemini"
        elif os.getenv("OPENAI_API_KEY"):
            provider = "openai"
        elif os.getenv("ANTHROPIC_API_KEY"):
            provider = "claude"
        else:
            provider = "mock"

    orchestrator = Orchestrator(
        target_path_or_url=args.path,
        provider=provider,
        model=args.model,
        instant=args.instant
    )

    try:
        readme_path, showroom_path = orchestrator.run()
        
        # Post-generation preview prompt
        if not args.instant:
            launch_prev = input("\nWould you like to preview the generated README and launch the showroom site? (y/n, default: y): ")
            if launch_prev.lower().strip() != 'n':
                previewer = Previewer(readme_path, showroom_path)
                previewer.show_in_terminal()
                if Path(showroom_path).exists():
                    previewer.launch_showroom_server(port=args.port)
        else:
            console.print("\n[green]Generation complete. Run with --preview -p <path> to launch the visual showroom viewer.[/green]")

    except Exception as e:
        console.print(f"\n[red]Execution error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
