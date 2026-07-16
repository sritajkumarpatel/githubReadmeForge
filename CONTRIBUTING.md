# Contributing to githubReadmeForge

Thanks for your interest in contributing! This guide will help you get set up and submitting PRs quickly.

## Quick Setup

```bash
# Clone the repo
git clone https://github.com/your-username/githubReadmeForge.git
cd githubReadmeForge

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install as editable package (optional, enables `readme-forge` CLI command)
pip install -e .

# Run the CLI in mock mode (no API keys needed)
python main.py --path . --instant

# Run the web server
python server.py --port 8082
```

## Architecture at a Glance

```
User → CLI (cli.py) or Web UI (server.py + web/)
         ↓
    Orchestrator
    ├── ReaderAgent    → Scans codebase files & tree structure
    ├── AnalyzerAgent  → Extracts tech stack, features, architecture (via LLM)
    └── WriterAgent    → Generates README markdown + Showroom HTML (via LLM)
```

## Where to Make Changes

| Goal | File(s) |
|------|---------|
| Add an LLM provider | `readme_forge/llm.py`, `cli.py`, `server.py` |
| Improve README output quality | `readme_forge/agents/writer.py` (system prompt) |
| Extract more codebase context | `readme_forge/agents/reader.py` |
| Change analysis schema | `readme_forge/agents/analyzer.py` |
| Update web UI | `web/index.html`, `web/styles.css`, `web/app.js` |
| Change CLI arguments | `readme_forge/cli.py` |

## Pull Request Guidelines

1. **One feature per PR** — keep changes focused and reviewable
2. **Test with mock mode** — ensure `python main.py --path . --instant` works without API keys
3. **Test the web UI** — if your change affects generation, verify it in the browser dashboard too
4. **Update docs** — if you add a feature, update the README and `.agents/AGENTS.md`
5. **No breaking changes** to the mock fallback — it's the demo mode

## Code Style

- Python 3.10+ with type hints on public functions
- Use Rich for CLI output (no bare `print()` for user-facing messages)
- Vanilla CSS in the web UI — no frameworks
- Docstrings on all public methods

## Questions?

Open an issue or start a discussion. We're happy to help!
