import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from readme_forge.llm import LLMClient
from readme_forge.agents.reader import ReaderAgent
from readme_forge.agents.analyzer import AnalyzerAgent
from readme_forge.agents.writer import WriterAgent

# Off-topic patterns that should be rejected in interactive Q&A answers.
_OFF_TOPIC_PATTERNS = (
    "write a program", "write a function", "write code to", "write a script",
    "write a sum", "sum program", "calculator program", "math program",
    "solve this", "fibonacci", "sorting algorithm",
)


class Orchestrator:
    def __init__(self, target_path_or_url, provider=None, model=None, instant=False, lang="en",
                 style="visual_rich", output_dir=None):
        self.target_path_or_url = target_path_or_url
        self.instant = instant
        self.lang = lang or "en"
        self.style = style or "visual_rich"
        self.output_dir_override = output_dir  # Path or None
        self.console = Console()

        self.llm_client = LLMClient(provider=provider, model=model)
        self.reader = ReaderAgent(target_path_or_url)
        self.analyzer = AnalyzerAgent(self.llm_client)
        self.writer = WriterAgent(self.llm_client)

    # ── Output directory — computed ONCE to avoid duplication drift ────────

    def _resolve_output_dir(self) -> Path:
        """Single source of truth for the output directory."""
        if self.output_dir_override:
            d = Path(self.output_dir_override)
        elif self.reader.is_temp:
            d = Path("./readme_forge_output")
        else:
            d = Path(self.reader.local_path)
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ── Main pipeline ──────────────────────────────────────────────────────

    def run(self):
        """Runs the full scan → analyze → write → save pipeline."""
        self.console.print("\n[bold blue]🛠️ githubReadmeForge Orchestrator Started[/bold blue]")
        self.console.print(
            f"Provider: [bold green]{self.llm_client.provider}[/bold green], "
            f"Model: [bold green]{self.llm_client.model}[/bold green]"
        )

        if not self.llm_client.is_configured():
            self.console.print("[red]Error: LLM Client is not configured. Please provide API credentials.[/red]")
            raise Exception("LLM provider not configured")

        scan_results = None
        analysis = None

        try:
            # ── 1. READ ────────────────────────────────────────────────────
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                          transient=True) as progress:
                progress.add_task(description="Scanning codebase...", total=None)
                self.reader.setup()
                scan_results = self.reader.scan_codebase()

            self.console.print("✓ Codebase scanned successfully.")
            self.console.print("  Found tree structure, configuration files, and primary source files.")

            # ── 2. ANALYZE ────────────────────────────────────────────────
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                          transient=True) as progress:
                progress.add_task(description="Analyzing codebase architecture and flow...", total=None)
                analysis = self.analyzer.analyze(scan_results)

            self.console.print("✓ Codebase analyzed successfully.")
            self.console.print(f"\n[bold]Project Summary:[/bold] {analysis.get('project_persona')}")
            self.console.print(
                f"[bold]Detected Type:[/bold] [cyan]{analysis.get('project_type', 'unknown')}[/cyan]  "
                f"[bold]Confidence:[/bold] "
                f"{int(analysis.get('classification', {}).get('confidence', 1.0) * 100)}%"
            )
            self.console.print(f"[bold]Tech Stack:[/bold] {', '.join(analysis.get('tech_stack', []))}")

            # Warn when classification confidence is low
            confidence = analysis.get("classification", {}).get("confidence", 1.0)
            if confidence < 0.5:
                self.console.print(
                    "[yellow]⚠ Classification confidence is low "
                    f"({int(confidence * 100)}%). "
                    "Review the design brief carefully before generating.[/yellow]"
                )

            self._show_improvements_table(analysis.get("improvements", []))

            # ── 3. INTERACTIVE Q&A (optional) ─────────────────────────────
            interactive_answers = None
            if not self.instant:
                interactive_answers = self._run_interactive_prompts(analysis)
            else:
                self.console.print("\n[cyan]Instant mode active. Skipping questions...[/cyan]")

            # ── 4. WRITE ──────────────────────────────────────────────────
            output_dir = self._resolve_output_dir()

            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"),
                          transient=True) as progress:
                progress.add_task(description="Forging README.md...", total=None)
                readme_md = self.writer.generate_readme(
                    scan_results=scan_results,
                    analysis=analysis,
                    interactive_answers=interactive_answers,
                    style=self.style,
                    output_dir=output_dir,
                    target_path_or_url=self.target_path_or_url,
                    lang=self.lang,
                )

            # ── 5. SAVE ───────────────────────────────────────────────────
            readme_path = output_dir / "README.md"

            # In interactive mode, offer to avoid overwriting existing README
            if not self.instant and readme_path.exists():
                overwrite = input(
                    f"\nREADME.md already exists in target directory. "
                    "Overwrite? (y/n, default: y): "
                )
                if overwrite.lower().strip() == "n":
                    readme_path = output_dir / "README_new.md"
                    self.console.print(f"Saving new README as: [cyan]{readme_path.name}[/cyan]")

            readme_path.write_text(readme_md, encoding="utf-8")

            self.console.print("\n[bold green]🎉 README.md Forged successfully![/bold green]")
            self.console.print("Generated file location:")
            self.console.print(f"  📝 [bold]README[/bold]: {readme_path.resolve()}")

            if self.reader.is_temp:
                self.console.print(
                    "\n[yellow]Note: Cloned repository outputs saved in "
                    "'./readme_forge_output/' folder.[/yellow]"
                )

            return str(readme_path)

        finally:
            self.reader.cleanup()

    # ── Rich terminal helpers ──────────────────────────────────────────────

    def _show_improvements_table(self, improvements):
        """Display improvement opportunities in a styled Rich table."""
        if not improvements:
            return

        table = Table(
            title="[bold yellow]Analysis & Improvement Opportunities[/bold yellow]",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("ID", style="dim", width=4)
        table.add_column("Category", style="cyan", width=15)
        table.add_column("Issue / Enhancement Opportunity", style="bold white")
        table.add_column("Details", style="dim")

        for imp in improvements:
            table.add_row(
                str(imp.get("id", "")),
                str(imp.get("type", "General")),
                str(imp.get("title", "")),
                str(imp.get("description", "")),
            )

        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")

    # ── Interactive prompts with guardrails ────────────────────────────────

    def _validate_answer(self, answer: str) -> str | None:
        """Return None and print a warning if the answer is off-topic."""
        lower = answer.lower()
        if any(pattern in lower for pattern in _OFF_TOPIC_PATTERNS):
            self.console.print(
                "[yellow]⚠ That input appears unrelated to README documentation. "
                "Skipping this answer.[/yellow]"
            )
            return None
        return answer

    def _run_interactive_prompts(self, analysis):
        """Walk the user through interactive README customisation options."""
        self.console.print("[bold cyan]=== Interactive Q&A Mode ===[/bold cyan]")
        self.console.print(
            "Answer the questions below to customise your README, or press Enter to skip each one."
        )

        answers = []

        # Q1: Persona refinement
        raw = input("\n1. Refine the project persona summary? (Leave blank to keep default):\n> ")
        validated = self._validate_answer(raw.strip()) if raw.strip() else None
        if validated:
            answers.append(f"- Project Persona Override: {validated}")

        # Q2: Extra sections
        raw = input(
            "\n2. Any specific sections to add? "
            "(e.g. 'CLI parameters list', 'Contributing guidelines'):\n> "
        )
        validated = self._validate_answer(raw.strip()) if raw.strip() else None
        if validated:
            answers.append(f"- Custom Sections Requested: {validated}")

        # Q3: Usage example
        raw = input(
            "\n3. Paste a specific code snippet or CLI command for the Examples section:\n> "
        )
        validated = self._validate_answer(raw.strip()) if raw.strip() else None
        if validated:
            answers.append(f"- Preferred Usage Example:\n```\n{validated}\n```")

        # Q4: Contact info
        raw = input("\n4. Author name or email for the support/contact section:\n> ")
        validated = self._validate_answer(raw.strip()) if raw.strip() else None
        if validated:
            answers.append(f"- Contact Information: {validated}")

        # Q5: Language override (not free-text, just a code — safe)
        raw = input(
            f"\n5. Target language code (e.g. 'zh-CN', 'es', "
            f"or Enter to keep default '{self.lang}'):\n> "
        )
        if raw.strip():
            self.lang = raw.strip()

        return "\n".join(answers) if answers else None
