import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from readme_forge.llm import LLMClient
from readme_forge.agents.reader import ReaderAgent
from readme_forge.agents.analyzer import AnalyzerAgent
from readme_forge.agents.writer import WriterAgent

class Orchestrator:
    def __init__(self, target_path_or_url, provider=None, model=None, instant=False):
        self.target_path_or_url = target_path_or_url
        self.instant = instant
        self.console = Console()
        
        self.llm_client = LLMClient(provider=provider, model=model)
        self.reader = ReaderAgent(target_path_or_url)
        self.analyzer = AnalyzerAgent(self.llm_client)
        self.writer = WriterAgent(self.llm_client)

    def run(self):
        """Runs the orchestration process."""
        self.console.print("\n[bold blue]🛠️ githubReadmeForge Orchestrator Started[/bold blue]")
        self.console.print(f"Provider: [bold green]{self.llm_client.provider}[/bold green], Model: [bold green]{self.llm_client.model}[/bold green]")
        
        if not self.llm_client.is_configured():
            self.console.print("[yellow]LLM Client is not configured. Falling back to mock generator.[/yellow]")

        scan_results = None
        analysis = None

        try:
            # 1. READ PHASE
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                progress.add_task(description="Scanning codebase...", total=None)
                self.reader.setup()
                scan_results = self.reader.scan_codebase()

            self.console.print("✓ Codebase scanned successfully.")
            self.console.print(f"  Found tree structure, configuration files, and primary source files.")

            # 2. ANALYZE PHASE
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                progress.add_task(description="Analyzing codebase architecture and flow...", total=None)
                analysis = self.analyzer.analyze(scan_results)

            self.console.print("✓ Codebase analyzed successfully.")

            # Display Tech Stack & Summary
            self.console.print(f"\n[bold]Project Summary:[/bold] {analysis.get('project_persona')}")
            self.console.print(f"[bold]Detected Tech Stack:[/bold] {', '.join(analysis.get('tech_stack', []))}")

            # Display improvements list
            self._show_improvements_table(analysis.get("improvements", []))

            interactive_answers = None
            if not self.instant:
                interactive_answers = self._run_interactive_prompts(analysis)
            else:
                self.console.print("\n[cyan]Instant mode active. Skipping questions...[/cyan]")

            # 3. WRITE PHASE
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                progress.add_task(description="Forging README.md and Showroom HTML...", total=None)
                readme_md = self.writer.generate_readme(scan_results, analysis, interactive_answers)
                showroom_html = self.writer.generate_showroom_html(readme_md, analysis)

            # 4. SAVE PHASE
            # Save files to target directory
            # If target is remote (git url), reader.local_path points to temp dir.
            # We can save it in the current working directory, or target path.
            # Let's save in reader.local_path or output to user's local path if specified.
            output_dir = Path(self.reader.local_path)
            
            # If it's cloned/temporary, let's write to output folder in current dir
            if self.reader.is_temp:
                output_dir = Path("./readme_forge_output")
                output_dir.mkdir(exist_ok=True)
                
            readme_path = output_dir / "README.md"
            showroom_path = output_dir / "showroom.html"

            # In interactive mode, ask if user wants to overwrite
            if not self.instant and readme_path.exists():
                overwrite = input(f"\nREADME.md already exists in target directory. Overwrite? (y/n, default: y): ")
                if overwrite.lower().strip() == 'n':
                    readme_path = output_dir / "README_new.md"
                    self.console.print(f"Saving new README as: [cyan]{readme_path.name}[/cyan]")

            readme_path.write_text(readme_md, encoding="utf-8")
            showroom_path.write_text(showroom_html, encoding="utf-8")

            self.console.print("\n[bold green]🎉 README.md and showroom.html Forged successfully![/bold green]")
            self.console.print(f"Generated files location:")
            self.console.print(f"  📝 [bold]README[/bold]: {readme_path.resolve()}")
            self.console.print(f"  🌐 [bold]Showroom HTML[/bold]: {showroom_path.resolve()}")
            
            if self.reader.is_temp:
                self.console.print("\n[yellow]Note: Cloned repository outputs saved in './readme_forge_output/' folder.[/yellow]")

            return str(readme_path), str(showroom_path)

        finally:
            self.reader.cleanup()

    def _show_improvements_table(self, improvements):
        """Displays improvements in a styled table."""
        if not improvements:
            return
            
        table = Table(title="[bold yellow]Analysis & Improvement Opportunities[/bold yellow]", show_header=True, header_style="bold magenta")
        table.add_column("ID", style="dim", width=4)
        table.add_column("Category", style="cyan", width=15)
        table.add_column("Issue / Enhancement Opportunity", style="bold white")
        table.add_column("Details", style="dim")

        for imp in improvements:
            table.add_row(
                str(imp.get("id", "")),
                str(imp.get("type", "General")),
                str(imp.get("title", "")),
                str(imp.get("description", ""))
            )

        self.console.print("\n")
        self.console.print(table)
        self.console.print("\n")

    def _run_interactive_prompts(self, analysis):
        """Walks the user through interactive customization options."""
        self.console.print("[bold cyan]=== Interactive Q&A Mode ===[/bold cyan]")
        self.console.print("Please answer the following brief questions to customize your README, or press Enter to skip.")
        
        answers = []
        
        # Q1: Custom Persona adjustment
        q_persona = input("\n1. Would you like to refine the project persona summary? (Leave blank to keep default):\n> ")
        if q_persona.strip():
            answers.append(f"- Project Persona Overrides: {q_persona.strip()}")
            
        # Q2: Extra sections
        q_sections = input("\n2. Any specific sections you want to add? (e.g. 'CLI parameters list', 'Contributing guidelines')\n> ")
        if q_sections.strip():
            answers.append(f"- Custom Sections Requested: {q_sections.strip()}")
            
        # Q3: Main usage example code
        q_examples = input("\n3. Paste a specific code snippet or CLI command you want displayed in the Examples section:\n> ")
        if q_examples.strip():
            answers.append(f"- Preferred Usage Example:\n```\n{q_examples.strip()}\n```")
            
        # Q4: Contact / Custom License
        q_contact = input("\n4. Author name or email for support / contact section:\n> ")
        if q_contact.strip():
            answers.append(f"- Contact Information: {q_contact.strip()}")

        return "\n".join(answers) if answers else None
