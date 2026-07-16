import os
import json
import requests

class LLMClient:
    def __init__(self, provider=None, model=None, api_key=None, base_url=None):
        self.provider = provider or os.getenv("README_FORGE_PROVIDER", "mock").lower()
        self.model = model or os.getenv("README_FORGE_MODEL")
        self.api_key = api_key
        self.base_url = base_url

        # Auto-configure based on provider and env vars if not explicitly provided
        if self.provider == "gemini":
            self.api_key = self.api_key or os.getenv("GEMINI_API_KEY")
            self.model = self.model or "gemini-1.5-flash"
        elif self.provider == "openai":
            self.api_key = self.api_key or os.getenv("OPENAI_API_KEY")
            self.model = self.model or "gpt-4o-mini"
        elif self.provider == "claude":
            self.api_key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
            self.model = self.model or "claude-3-5-sonnet-20240620"
        elif self.provider == "ollama":
            self.base_url = self.base_url or os.getenv("OLLAMA_HOST", "http://localhost:11434")
            self.model = self.model or "llama3"
        else:
            self.provider = "mock"
            self.model = "mock-model"

    def is_configured(self):
        if self.provider == "mock":
            return True
        if self.provider == "ollama":
            # Just check if we have a base_url, we'll try to reach it during call
            return bool(self.base_url)
        return bool(self.api_key)

    def generate(self, system_prompt, user_prompt, response_format_json=False):
        """Generates text from the LLM, with support for JSON response format if supported/requested."""
        if self.provider == "mock":
            return self._mock_generate(system_prompt, user_prompt, response_format_json)

        try:
            if self.provider == "gemini":
                return self._generate_gemini(system_prompt, user_prompt, response_format_json)
            elif self.provider == "openai":
                return self._generate_openai(system_prompt, user_prompt, response_format_json)
            elif self.provider == "claude":
                return self._generate_claude(system_prompt, user_prompt, response_format_json)
            elif self.provider == "ollama":
                return self._generate_ollama(system_prompt, user_prompt, response_format_json)
        except Exception as e:
            # Fallback to mock with warning message if LLM fails
            print(f"\n[Warning] LLM API Call failed ({e}). Falling back to mock generator.")
            return self._mock_generate(system_prompt, user_prompt, response_format_json)

    def _generate_gemini(self, system_prompt, user_prompt, response_format_json):
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        
        config = {}
        if response_format_json:
            config["response_mime_type"] = "application/json"
            
        model = genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt,
            generation_config=config
        )
        response = model.generate_content(user_prompt)
        return response.text

    def _generate_openai(self, system_prompt, user_prompt, response_format_json):
        from openai import OpenAI
        client = OpenAI(api_key=self.api_key)
        
        kwargs = {}
        if response_format_json:
            kwargs["response_format"] = {"type": "json_object"}
            
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            **kwargs
        )
        return response.choices[0].message.content

    def _generate_claude(self, system_prompt, user_prompt, response_format_json):
        from anthropic import Anthropic
        client = Anthropic(api_key=self.api_key)
        
        # System instructions go to the system param in Claude Messages API
        response = client.messages.create(
            model=self.model,
            max_tokens=4000,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text

    def _generate_ollama(self, system_prompt, user_prompt, response_format_json):
        url = f"{self.base_url.rstrip('/')}/api/generate"
        prompt = f"System Instruction:\n{system_prompt}\n\nUser Input:\n{user_prompt}"
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if response_format_json:
            data["format"] = "json"
            
        res = requests.post(url, json=data, timeout=60)
        res.raise_for_status()
        return res.json().get("response", "")

    def _mock_generate(self, system_prompt, user_prompt, response_format_json):
        """Simulates LLM responses with rich, narrative-driven output for demo/testing purposes."""
        # Detect if it's the analyzer requesting JSON structure
        if "improvement points" in user_prompt.lower() or "list_improvements" in system_prompt.lower() or response_format_json:
            mock_analysis = {
                "tech_stack": ["Python 3.10+", "Rich CLI", "Multi-LLM (Gemini/OpenAI/Claude/Ollama)", "HTTP Server"],
                "project_persona": "An AI-powered multi-agent CLI & web tool that analyzes codebases and generates professional, narrative-driven README.md files with interactive HTML showcases.",
                "problem_statement": "Developers spend hours writing and maintaining README documentation that quickly becomes outdated. New contributors bounce from repos with poor or missing docs, and great code goes unused because nobody understands what it does or how to use it.",
                "solution_narrative": "githubReadmeForge uses a three-agent AI pipeline (Reader → Analyzer → Writer) to scan any codebase, extract architectural context, and generate a comprehensive README with narrative problem/solution sections, architecture diagrams, feature docs, and configuration tables — plus an interactive HTML showcase site.",
                "key_features": [
                    {
                        "name": "Multi-LLM Support",
                        "description": "Switch between Gemini, OpenAI, Claude, or Ollama. Falls back to mock generator when no API keys are configured.",
                        "category": "Integration"
                    },
                    {
                        "name": "Dual Interface (CLI + Web)",
                        "description": "Use the terminal CLI for quick generation or the web dashboard for a visual experience with real-time analysis scores and live preview.",
                        "category": "Developer Experience"
                    },
                    {
                        "name": "Adaptive Hero Banners",
                        "description": "Automatically generates dark/light SVG hero banners that respond to GitHub's theme preference — no external tools required.",
                        "category": "Visual"
                    },
                    {
                        "name": "Showroom HTML Generator",
                        "description": "Every generation produces an interactive glassmorphic HTML showcase with tabbed docs, architecture diagrams, and copy-paste ready content.",
                        "category": "Core"
                    },
                    {
                        "name": "Internationalization (i18n)",
                        "description": "Generate READMEs in any language using the --lang flag. AI translates narrative content while preserving code blocks.",
                        "category": "Core"
                    },
                    {
                        "name": "Interactive & Instant Modes",
                        "description": "Interactive mode walks through customization questions. Instant mode (--instant) generates everything in one shot with zero prompts.",
                        "category": "Developer Experience"
                    },
                    {
                        "name": "Guardrails & Safety",
                        "description": "Built-in safety checks prevent the AI from being hijacked for off-topic tasks. Strictly enforces README-only generation.",
                        "category": "Security"
                    }
                ],
                "api_endpoints": [
                    {
                        "method": "POST",
                        "path": "/api/analyze",
                        "description": "Scans a codebase and returns structural analysis including tech stack, features, and improvement suggestions."
                    },
                    {
                        "method": "POST",
                        "path": "/api/generate",
                        "description": "Generates README markdown and Showroom HTML from analysis data with style and language options."
                    }
                ],
                "config_variables": [
                    {
                        "name": "GEMINI_API_KEY",
                        "description": "Google Gemini API key for AI generation",
                        "required": False,
                        "default": ""
                    },
                    {
                        "name": "OPENAI_API_KEY",
                        "description": "OpenAI API key for GPT-based generation",
                        "required": False,
                        "default": ""
                    },
                    {
                        "name": "ANTHROPIC_API_KEY",
                        "description": "Anthropic Claude API key",
                        "required": False,
                        "default": ""
                    },
                    {
                        "name": "OLLAMA_HOST",
                        "description": "Ollama server URL for local LLM generation",
                        "required": False,
                        "default": "http://localhost:11434"
                    },
                    {
                        "name": "README_FORGE_PROVIDER",
                        "description": "Force a specific LLM provider instead of auto-detection",
                        "required": False,
                        "default": "auto-detect"
                    },
                    {
                        "name": "README_FORGE_MODEL",
                        "description": "Override the default model name for the selected provider",
                        "required": False,
                        "default": "provider default"
                    }
                ],
                "cli_commands": [
                    {
                        "command": "python main.py --path . --instant",
                        "description": "Generate README for current directory in instant mode"
                    },
                    {
                        "command": "python main.py --path https://github.com/user/repo.git",
                        "description": "Generate README for a remote repository"
                    },
                    {
                        "command": "python main.py --path . --provider gemini --lang zh-CN",
                        "description": "Generate with Gemini AI in Chinese"
                    },
                    {
                        "command": "python main.py --path . --preview --port 8080",
                        "description": "Preview existing generated files in the browser"
                    },
                    {
                        "command": "python server.py --port 8082",
                        "description": "Start the web dashboard server"
                    }
                ],
                "improvements": [
                    {
                        "id": "1",
                        "title": "Missing visual architectural layout",
                        "description": "The current README lacks a Mermaid.js diagram showing how the CLI, agents, and LLMs interact in the pipeline.",
                        "type": "Structure"
                    },
                    {
                        "id": "2",
                        "title": "Inconsistent configuration documentation",
                        "description": "Environment variables and CLI flags are not documented in comprehensive tables with descriptions and defaults.",
                        "type": "Configuration"
                    },
                    {
                        "id": "3",
                        "title": "Missing narrative Problem/Solution sections",
                        "description": "The README jumps straight to technical details without explaining the pain point the tool solves or why developers need it.",
                        "type": "Structure"
                    }
                ],
                "connections": [
                    {"from": "CLI / Web UI", "to": "Orchestrator", "relationship": "User input triggers pipeline"},
                    {"from": "Orchestrator", "to": "Reader Agent", "relationship": "Dispatches codebase scan"},
                    {"from": "Reader Agent", "to": "Analyzer Agent", "relationship": "Passes scan_results"},
                    {"from": "Analyzer Agent", "to": "LLM Client", "relationship": "Sends analysis prompt"},
                    {"from": "LLM Client", "to": "Analyzer Agent", "relationship": "Returns structured JSON"},
                    {"from": "Orchestrator", "to": "Writer Agent", "relationship": "Passes scan + analysis"},
                    {"from": "Writer Agent", "to": "LLM Client", "relationship": "Sends generation prompt"},
                    {"from": "Writer Agent", "to": "Hero Generator", "relationship": "Generates SVG banners"},
                    {"from": "Writer Agent", "to": "README.md + showroom.html", "relationship": "Final output"}
                ]
            }
            return json.dumps(mock_analysis, indent=2)

        # Detect if it's the writer requesting README generation
        if "generate" in user_prompt.lower() or "readme" in user_prompt.lower():
            return """<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="assets/readme/hero-light.svg">
  <img alt="githubReadmeForge Banner" src="assets/readme/hero-light.svg" width="100%">
</picture>

<div align="center">

# githubReadmeForge ⚒️

### AI-Powered README Generation for Any Codebase

**Codebase → README. Three AI agents. One command.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![LLM](https://img.shields.io/badge/LLM-Gemini%20|%20OpenAI%20|%20Claude%20|%20Ollama-blueviolet?style=flat-square)](https://ai.google.dev)

</div>

---

## The Problem

Every developer has been there. You build something great — a CLI tool, a library, a full-stack app — and then comes the part nobody wants to do: **write the README**.

So you skip it. Or you write three bullet points and call it a day. And then:

- New contributors open the repo, see a barren README, and leave
- Your future self comes back 6 months later and has no idea how the project works
- The README you *did* write is now outdated because the codebase evolved

The result? **Great code that nobody uses because nobody understands it.**

Writing a good README requires understanding architecture, extracting the right code examples, creating diagrams, documenting configuration — it's hours of work that feels disconnected from actual development.

## The Solution

**githubReadmeForge** reads your codebase and writes the README for you.

Not a template. Not a form you fill out. It actually scans your files, maps your architecture, identifies your tech stack, extracts configuration variables, and generates a complete, narrative-driven README — plus an interactive HTML showcase site.

It works through a **three-agent AI pipeline**:

1. **Reader Agent** scans your codebase — tree structure, config files, entry points, docstrings
2. **Analyzer Agent** uses an LLM to extract meaning — tech stack, features, architecture connections, improvement opportunities
3. **Writer Agent** uses the analysis to forge a polished, structured README with diagrams, tables, and real examples

You can run it as a **CLI command** or through a **web dashboard**. Works with Gemini, OpenAI, Claude, Ollama, or completely offline with the mock generator.

---

## How It Works

```mermaid
graph LR
    A["📁 Your Codebase"] --> B["🔍 Reader Agent"]
    B --> C["🧠 Analyzer Agent"]
    C --> D["✍️ Writer Agent"]
    D --> E["📝 README.md"]
    D --> F["🌐 Showroom HTML"]

    style A fill:#1e293b,stroke:#3b82f6,color:#f3f4f6
    style B fill:#1e293b,stroke:#10b981,color:#f3f4f6
    style C fill:#1e293b,stroke:#8b5cf6,color:#f3f4f6
    style D fill:#1e293b,stroke:#f59e0b,color:#f3f4f6
    style E fill:#1e293b,stroke:#3b82f6,color:#f3f4f6
    style F fill:#1e293b,stroke:#3b82f6,color:#f3f4f6
```

### Agent Roles

| Agent | Responsibility | Input | Output |
|-------|---------------|-------|--------|
| **🔍 Reader** | Scans files, extracts tree structure, reads config & source code | Repository path or Git URL | `scan_results` (tree, configs, code context) |
| **🧠 Analyzer** | Identifies tech stack, features, architecture flow, improvements | `scan_results` | Structured JSON analysis |
| **✍️ Writer** | Generates narrative README + interactive Showroom HTML | `scan_results` + `analysis` | `README.md` + `showroom.html` |
| **🎯 Orchestrator** | Coordinates pipeline, handles interactive Q&A, manages output | User CLI/API input | Orchestrated agent execution |
| **🎨 Hero Generator** | Creates dark/light adaptive SVG banners | Project name + tech stack | `hero-dark.svg` + `hero-light.svg` |

### Input → Output Pipeline

```
┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐
│   YOUR CODEBASE  │     │   ANALYSIS JSON  │     │    FINAL OUTPUT  │
│                  │     │                  │     │                  │
│  • File tree     │────▶│  • Tech stack    │────▶│  • README.md     │
│  • Config files  │     │  • Features      │     │  • showroom.html │
│  • Source code   │     │  • Architecture  │     │  • Hero SVGs     │
│  • Existing docs │     │  • Improvements  │     │  • Mermaid diagrams│
└──────────────────┘     └──────────────────┘     └──────────────────┘
     Reader Agent           Analyzer Agent           Writer Agent
```

---

## Features

### 🤖 Multi-LLM Support
Bring your own AI provider. Switch between Gemini, OpenAI, Claude, or run fully local with Ollama. Falls back gracefully to a mock generator when no API keys are configured — perfect for demos and CI.

### 🌐 Dual Interface (CLI + Web Dashboard)
Use the **CLI** for quick terminal-based generation with Rich UI formatting, or launch the **Web Dashboard** for a visual experience with real-time analysis scores, interactive customization, and live preview tabs.

### 🎨 Adaptive Hero Banners
Automatically generates dark/light SVG hero banners that respond to GitHub's theme preference using the `<picture>` tag — no external image tools required. Pure Python SVG generation.

### 🏛️ Showroom HTML Generator
Every generation produces not just a README, but an interactive **Showroom website** with tabbed documentation, architecture flow visualizations, and a premium glassmorphic dark UI.

### 🌍 Internationalization (i18n)
Generate READMEs in any language. Pass `--lang zh-CN` for Chinese, `--lang es` for Spanish — the AI translates all narrative content while preserving code blocks and technical terms.

### 🛡️ Guardrails & Safety
Built-in safety checks prevent the AI from being hijacked for off-topic tasks. The system strictly enforces README-only generation — both server-side and in the LLM prompt.

### 🔄 Interactive & Instant Modes
**Interactive mode** walks you through customization questions (persona, sections, examples, contact info). **Instant mode** (`--instant`) generates everything in one shot with zero prompts.

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/your-username/githubReadmeForge.git
cd githubReadmeForge

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### CLI Usage

```bash
# Generate README for current directory (instant mode, mock LLM)
python main.py --path . --instant

# Generate with Gemini AI
export GEMINI_API_KEY="your-key"
python main.py --path . --provider gemini

# Generate for a remote repository
python main.py --path https://github.com/user/repo.git --instant

# Interactive mode with language translation
python main.py --path ./my-project --lang zh-CN
```

### Web Dashboard

```bash
# Start the web server
python server.py --port 8082

# Open http://localhost:8082 in your browser
```

---

## Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `GEMINI_API_KEY` | Google Gemini API key | No* | — |
| `OPENAI_API_KEY` | OpenAI API key | No* | — |
| `ANTHROPIC_API_KEY` | Anthropic Claude API key | No* | — |
| `OLLAMA_HOST` | Ollama server URL | No | `http://localhost:11434` |
| `README_FORGE_PROVIDER` | Force a specific provider | No | Auto-detect |
| `README_FORGE_MODEL` | Override default model | No | Provider default |

> \\* At least one LLM provider key is recommended. Without any, the tool uses the mock generator.

### CLI Flags

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--path` | `-p` | Repository path or Git URL | `.` |
| `--provider` | — | LLM provider (`gemini`, `openai`, `claude`, `ollama`, `mock`) | Auto-detect |
| `--model` | — | Model name override | Provider default |
| `--instant` | `-i` | Skip interactive questions | `false` |
| `--preview` | `-v` | Preview existing generated files | `false` |
| `--port` | — | Port for preview/showroom server | `8080` |
| `--lang` | `-l` | Target language code | `en` |

---

## API Reference

### `POST /api/analyze`

Scans a codebase and returns structural analysis.

**Request:**
```json
{
  "path": "./my-project",
  "provider": "gemini",
  "model": "gemini-1.5-flash",
  "api_key": "optional-override"
}
```

**Response:**
```json
{
  "success": true,
  "score": 65,
  "scan": { "path": "...", "tree": "..." },
  "analysis": {
    "tech_stack": ["Python", "Flask"],
    "project_persona": "A REST API for...",
    "key_features": [...]
  }
}
```

### `POST /api/generate`

Generates README and Showroom HTML from analysis data.

**Request:**
```json
{
  "scan": { "..." },
  "analysis": { "..." },
  "provider": "gemini",
  "style": "visual_rich",
  "lang": "en"
}
```

**Response:**
```json
{
  "success": true,
  "readme": "# Project Name\\n...",
  "showroom": "<!DOCTYPE html>..."
}
```

---

## Repository Structure

```
githubReadmeForge/
├── main.py                          # CLI entry point
├── server.py                        # Web API server
├── setup.py                         # Package installation
├── requirements.txt                 # Dependencies
├── .env.example                     # Environment variable template
├── readme_forge/                    # Core package
│   ├── cli.py                       # CLI argument parsing
│   ├── llm.py                       # Multi-provider LLM client
│   ├── hero_generator.py            # SVG banner generator
│   ├── preview.py                   # Terminal preview server
│   └── agents/
│       ├── reader.py                # Codebase scanner
│       ├── analyzer.py              # Structural analysis
│       ├── writer.py                # README generator
│       └── orchestrator.py          # Pipeline coordinator
├── web/                             # Web dashboard
│   ├── index.html
│   ├── styles.css
│   └── app.js
└── .agents/                         # AI assistant config
    ├── AGENTS.md
    └── skills/
```

---

## Contributing & License

Contributions are welcome! See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions and PR guidelines.

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ⚒️ by developers who got tired of writing READMEs by hand.**

</div>
"""

        return "Mock Response: Operation completed successfully."
