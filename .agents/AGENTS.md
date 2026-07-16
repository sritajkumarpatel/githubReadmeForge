# githubReadmeForge — Project Guidelines

## Architecture Overview

githubReadmeForge is a **multi-agent README generation tool** with dual interfaces:

- **CLI** (`main.py` → `readme_forge/cli.py`): Terminal-based with Rich UI, interactive & instant modes
- **Web Server** (`server.py` → `web/`): Browser-based dashboard with real-time analysis & generation

### Agent Pipeline

```
User Input → ReaderAgent → AnalyzerAgent → WriterAgent → README.md + showroom.html
```

| Agent | File | Responsibility |
|-------|------|----------------|
| **ReaderAgent** | `readme_forge/agents/reader.py` | Scans codebase, extracts tree structure, config files, and source code context |
| **AnalyzerAgent** | `readme_forge/agents/analyzer.py` | Uses LLM to extract tech stack, features, architecture connections, and improvement suggestions |
| **WriterAgent** | `readme_forge/agents/writer.py` | Uses LLM + analysis data to generate README markdown and Showroom HTML |
| **Orchestrator** | `readme_forge/agents/orchestrator.py` | Coordinates the pipeline, handles interactive Q&A, manages file output |
| **HeroGenerator** | `readme_forge/hero_generator.py` | Generates dark/light SVG hero banners without external dependencies |

### LLM Integration

- **Client**: `readme_forge/llm.py` — Unified interface supporting Gemini, OpenAI, Claude, Ollama, and a mock fallback
- **Mock mode** is the default when no API keys are set. It returns a pre-built template for demo/testing
- All LLM system prompts live in the agent files (`writer.py`, `analyzer.py`), never in `llm.py`

## Code Conventions

- **Python 3.10+** required
- **Type hints** preferred for function signatures
- **Rich library** for all CLI output (tables, progress spinners, styled text)
- **No external CSS frameworks** in the web UI — vanilla CSS with custom properties
- **Docstrings** on all public methods

## File Organization

```
readme_forge/          # Core Python package
  agents/              # Agent implementations (reader, analyzer, writer, orchestrator)
  cli.py               # CLI argument parsing and entry point
  llm.py               # LLM provider abstraction layer
  hero_generator.py    # SVG banner generation (no external deps)
  preview.py           # Terminal preview and local server for showroom
server.py              # HTTP API server for web UI
web/                   # Frontend (HTML, CSS, JS — no build tools)
assets/readme/         # Generated SVG hero banners
```

## Key Rules

1. **Guardrails**: Both `server.py` and `writer.py` enforce guardrails against off-topic LLM requests. Always maintain these.
2. **Mock fallback**: Every LLM call must gracefully fall back to mock if the API fails. See `llm.py:generate()`.
3. **No hardcoded paths**: Use `Path` objects and relative references. The tool must work on any codebase.
4. **CORS enabled**: The server allows cross-origin requests for local development.
5. **Environment variables**: Provider keys use standard env var names (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Never log or expose them.

## Testing

- Run with `--provider mock` to test without API keys
- The web UI at `http://localhost:8082` exercises the full pipeline
- CLI: `python main.py --path . --instant` for quick validation
