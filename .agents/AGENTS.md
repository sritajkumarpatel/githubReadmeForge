# githubReadmeForge — Project Guidelines

## Architecture Overview

githubReadmeForge is a **multi-agent README generation tool** with dual interfaces:

- **CLI** (`main.py` → `readme_forge/cli.py`): Terminal-based with Rich UI, instant mode
- **Web Server** (`server.py` → `web/`): Browser-based dashboard with real-time analysis & generation

### Agent Pipeline

```
User Input → ReaderAgent → AnalyzerAgent → WriterAgent → README.md + showroom.html
```

| Agent | File | Responsibility |
|-------|------|----------------|
| **ReaderAgent** | `readme_forge/agents/reader.py` | Scans codebase, extracts tree structure, config files, source code context, and existing README |
| **AnalyzerAgent** | `readme_forge/agents/analyzer.py` | Uses LLM to extract tech stack, features, architecture, project type, maturity classification, and improvement suggestions |
| **WriterAgent** | `readme_forge/agents/writer.py` | Uses LLM + analysis data to generate README markdown and Showroom HTML |

### Project Classification

The AnalyzerAgent classifies projects along two dimensions:

**Project Type:**
- `learning`: Tutorial projects, starter templates, educational code
- `poc`: Proof-of-concept or prototype projects
- `library`: Reusable packages/modules (npm/pypi/crates.io)
- `application`: Full web/desktop applications
- `cli`: Command-line tools
- `api`: Backend API services
- `minimal`: Small utility scripts

**Project Maturity:**
- `production`: Stable, well-tested, CI/CD, comprehensive docs
- `development`: Active development, basic functionality working
- `poc`: Early prototype, incomplete or experimental
- `unknown`: Unable to determine from available information

### LLM Integration

- **Client**: `readme_forge/llm.py` — Unified interface supporting Gemini, OpenAI, Claude, Ollama, OpenCode
- All LLM system prompts live in the agent files (`writer.py`, `analyzer.py`), never in `llm.py`

### README Style System (5 styles)

The WriterAgent supports 5 README styles, each modeled after a category of real top-rated GitHub projects. Style is auto-detected from `project_type`; the user can override in the dashboard.

| Style | Default for | Real-world model |
|---|---|---|
| `reference` | `library`, `cli`, `api` | Axios, ripgrep, FastAPI, gh CLI (user manuals) |
| `narrative` | `application` | Supabase, AppFlowy, Plausible (story-driven) |
| `tutorial` | `learning` | build-your-own-x, freeCodeCamp (learning path) |
| `showcase` | `demo` | AppFlowy, Phaser, httpie (visual product page) |
| `minimal` | `poc`, `minimal` | jq, Three.js, tldr (trailer for the docs) |

The mapping lives in `readme_forge/agents/contracts.py:INTENT_README_STYLE`. The Writer enforces per-style guardrails in `WriterAgent._get_style_guardrails()`.

Legacy style names (`visual_rich`, `minimalist`, `enterprise`) are auto-mapped to the new system for backward compatibility.

## Code Conventions

- **Python 3.10+** required
- **Type hints** preferred for function signatures
- **Rich library** for all CLI output (tables, progress spinners, styled text)
- **No external CSS frameworks** in the web UI — vanilla CSS with custom properties
- **Docstrings** on all public methods

## File Organization

```
readme_forge/          # Core Python package
  agents/              # Agent implementations (reader, analyzer, writer)
  cli.py               # CLI argument parsing and entry point
  llm.py               # LLM provider abstraction layer
  preview.py           # Terminal preview and local server for showroom
server.py              # HTTP API server for web UI
web/                   # Frontend (HTML, CSS, JS — no build tools)
web/assets/styles/     # Style preview thumbnails (visual-rich.svg, minimalist.svg, enterprise.svg)
```

## Key Rules

1. **Guardrails**: Both `server.py` and `writer.py` enforce guardrails against off-topic LLM requests. Always maintain these.
2. **No hero images**: The tool generates clean title blocks instead of hero SVGs. Keep README professional and fast-loading.
3. **No hardcoded paths**: Use `Path` objects and relative references. The tool must work on any codebase.
4. **CORS enabled**: The server allows cross-origin requests for local development.
5. **Environment variables**: Provider keys use standard env var names (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). Never log or expose them.

## Testing

- Run with `--provider mock` to test without API keys
- The web UI at `http://localhost:8080` exercises the full pipeline
- CLI: `python main.py --path . --instant` for quick validation
