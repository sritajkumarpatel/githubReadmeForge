import argparse
import sys
import os
from pathlib import Path
from rich.console import Console

from readme_forge.agents.orchestrator import Orchestrator
from readme_forge.preview import Previewer


def parse_args():
    parser = argparse.ArgumentParser(
        description="🛠️ githubReadmeForge: Multi-agent CLI to craft beautiful visual READMEs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  readme-forge --path .                          # Auto-detect provider from env
  readme-forge --path . --provider mock          # Test without an API key
  readme-forge --path . --style minimalist       # Minimalist theme
  readme-forge --path https://github.com/x/y    # Remote repository
  readme-forge --path . --output ./docs          # Custom output directory
        """
    )
    parser.add_argument(
        "--path", "-p",
        default=".",
        help="Local repository path or HTTP/Git URL of a remote repository. (default: current dir)"
    )
    parser.add_argument(
        "--provider",
        choices=["gemini", "openai", "claude", "ollama", "opencode", "mock"],
        help="LLM provider to use. Defaults to auto-detect from env vars, or 'mock' for testing."
    )
    parser.add_argument(
        "--model",
        help="Model name override (e.g. 'gemini-1.5-flash', 'gpt-4o-mini', 'llama3')."
    )
    parser.add_argument(
        "--style",
        choices=["visual_rich", "minimalist", "enterprise"],
        default="visual_rich",
        help="README formatting theme. (default: visual_rich)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory for the generated README.md. Defaults to the target repo directory."
    )
    parser.add_argument(
        "--instant", "-i",
        action="store_true",
        help="Skip interactive Q&A and generate immediately."
    )
    parser.add_argument(
        "--preview", "-v",
        action="store_true",
        help="Preview existing README.md in the terminal (skips generation)."
    )
    parser.add_argument(
        "--lang", "-l",
        default="en",
        help="Language for generated README (e.g. 'en', 'zh-CN', 'es'). (default: en)"
    )
    parser.add_argument(
        "--version",
        action="version",
        version="0.2.0",
        help="Show program version and exit."
    )

    return parser.parse_args()


def _resolve_provider(args_provider: str | None, console: Console) -> str:
    """Auto-detect LLM provider from environment, with graceful fallback to mock."""
    if args_provider:
        return args_provider

    if os.getenv("GEMINI_API_KEY"):
        provider = "gemini"
        console.print(f"[dim]Auto-detected provider: [bold]{provider}[/bold] (GEMINI_API_KEY)[/dim]")
        return provider
    if os.getenv("OPENAI_API_KEY"):
        provider = "openai"
        console.print(f"[dim]Auto-detected provider: [bold]{provider}[/bold] (OPENAI_API_KEY)[/dim]")
        return provider
    if os.getenv("ANTHROPIC_API_KEY"):
        provider = "claude"
        console.print(f"[dim]Auto-detected provider: [bold]{provider}[/bold] (ANTHROPIC_API_KEY)[/dim]")
        return provider

    # Graceful fallback — don't hard-exit, let the user know and use mock
    console.print(
        "\n[yellow]⚠ No API key found.[/yellow] "
        "Set [bold]GEMINI_API_KEY[/bold], [bold]OPENAI_API_KEY[/bold], or [bold]ANTHROPIC_API_KEY[/bold] "
        "to use a real LLM provider."
    )
    console.print(
        "[yellow]Falling back to [bold]mock[/bold] mode — output will be a demo template, not AI-generated.[/yellow]\n"
    )
    return "mock"


def main():
    args = parse_args()
    console = Console()

    # ── Preview mode: skip generation entirely ──────────────────────────────
    if args.preview:
        target_dir = Path(args.path).resolve()
        readme_path = target_dir / "README.md"

        if not readme_path.exists():
            readme_path = target_dir / "README_new.md"
            if not readme_path.exists():
                console.print(f"[red]Error: No README.md found at {target_dir}[/red]")
                sys.exit(1)

        previewer = Previewer(readme_path)
        previewer.show_in_terminal()
        return

    # ── Resolve provider ────────────────────────────────────────────────────
    provider = _resolve_provider(args.provider, console)

    # ── Resolve output directory ────────────────────────────────────────────
    output_dir = Path(args.output).resolve() if args.output else None

    orchestrator = Orchestrator(
        target_path_or_url=args.path,
        provider=provider,
        model=args.model,
        instant=args.instant,
        lang=args.lang,
        style=args.style,
        output_dir=output_dir,
    )

    try:
        readme_path = orchestrator.run()

        # Post-generation preview prompt (interactive mode only)
        if not args.instant:
            launch_prev = input("\nPreview the generated README in terminal? (y/n, default: y): ")
            if launch_prev.lower().strip() != "n":
                previewer = Previewer(readme_path)
                previewer.show_in_terminal()
        else:
            console.print(
                "\n[green]Done. Run [bold]readme-forge --preview -p "
                f"{Path(readme_path).parent}[/bold] to view in terminal.[/green]"
            )

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
