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
        elif self.provider == "opencode":
            self.base_url = self.base_url or os.getenv("OPENCODE_HOST", "http://127.0.0.1:4096")
            self.model = self.model or "anthropic/claude-3-5-sonnet-20241022"

    def is_configured(self):
        if self.provider == "mock":
            return True
        if self.provider == "ollama" or self.provider == "opencode":
            return bool(self.base_url)
        return bool(self.api_key)

    def get_available_models(self):
        """Fetch available models for the provider."""
        if self.provider == "mock":
            return ["mock-model-1", "mock-model-2"]
        elif self.provider == "openai":
            try:
                from openai import OpenAI
                client = OpenAI(api_key=self.api_key)
                models = client.models.list()
                return [m.id for m in models.data if not m.id.startswith('gpt-3.5-turbo-0301')]
            except Exception as e:
                return {"error": str(e)}
        elif self.provider == "claude":
            try:
                from anthropic import Anthropic
                client = Anthropic(api_key=self.api_key)
                return ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]
            except Exception as e:
                return {"error": str(e)}
        elif self.provider == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                return [m.name for m in genai.list_models()]
            except Exception as e:
                return {"error": str(e)}
        elif self.provider == "ollama":
            try:
                import requests
                response = requests.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
                return {"error": "Failed to fetch models"}
            except Exception as e:
                return {"error": str(e)}
        elif self.provider == "opencode":
            try:
                import requests
                response = requests.get(f"{self.base_url}/config/providers", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    models = []
                    for provider_id, provider_data in data.get("providers", {}).items():
                        if "models" in provider_data:
                            for model_id in provider_data["models"]:
                                models.append(f"{provider_id}/{model_id}")
                    return models if models else ["claude-3-5-sonnet-20241022"]
                return {"error": "Failed to fetch models"}
            except Exception as e:
                return {"error": str(e)}
        return []

    def generate(self, system_prompt, user_prompt, response_format_json=False):
        """Generates text from the LLM, with support for JSON response format if supported/requested."""
        try:
            if self.provider == "mock":
                return self._mock_generate(system_prompt, user_prompt, response_format_json)
            elif self.provider == "gemini":
                return self._generate_gemini(system_prompt, user_prompt, response_format_json)
            elif self.provider == "openai":
                return self._generate_openai(system_prompt, user_prompt, response_format_json)
            elif self.provider == "claude":
                return self._generate_claude(system_prompt, user_prompt, response_format_json)
            elif self.provider == "ollama":
                return self._generate_ollama(system_prompt, user_prompt, response_format_json)
            elif self.provider == "opencode":
                return self._generate_opencode(system_prompt, user_prompt, response_format_json)
        except Exception as e:
            if "not found on local Ollama server" in str(e):
                raise e
            raise Exception(f"LLM API call failed: {e}")

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
            max_tokens=8192,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.content[0].text

    def _generate_ollama(self, system_prompt, user_prompt, response_format_json):
        import requests
        url = f"{self.base_url.rstrip('/')}/api/generate"
        prompt = f"System Instruction:\n{system_prompt}\n\nUser Input:\n{user_prompt}"
        
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        if response_format_json:
            data["format"] = "json"
            
        try:
            res = requests.post(url, json=data, timeout=60)
            res.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code == 404:
                raise Exception(
                    f"Ollama model '{self.model}' not found on local Ollama server. "
                    f"Please run 'ollama pull {self.model}' in your terminal first."
                ) from e
            raise e
        return res.json().get("response", "")

    def _generate_opencode(self, system_prompt, user_prompt, response_format_json):
        import requests
        
        headers = {"Content-Type": "application/json"}
        
        create_resp = requests.post(
            f"{self.base_url.rstrip('/')}/session",
            headers=headers,
            json={},
            timeout=10
        )
        create_resp.raise_for_status()
        session = create_resp.json()
        session_id = session.get("id")
        
        if not session_id:
            raise Exception("Failed to create OpenCode session")
        
        parts = [{"type": "text", "text": user_prompt}]
        body = {
            "parts": parts,
            "system": system_prompt
        }
        
        if response_format_json:
            body["format"] = {
                "type": "json_schema",
                "schema": {
                    "type": "object",
                    "properties": {}
                }
            }
        
        msg_resp = requests.post(
            f"{self.base_url.rstrip('/')}/session/{session_id}/message",
            headers=headers,
            json=body,
            timeout=120
        )
        msg_resp.raise_for_status()
        result = msg_resp.json()
        
        parts = result.get("parts", [])
        text_parts = [p.get("text", "") for p in parts if p.get("type") == "text"]
        
        return "\n".join(text_parts)

    def _mock_generate(self, system_prompt, user_prompt, response_format_json):
        """Simulates LLM responses based on codebase signals in the prompt.

        The mock now inspects the user_prompt for project signals so that
        different repository types produce visibly different outputs — making
        development and testing of type-specific README behaviour practical.
        """
        import json

        if response_format_json:
            # ── Infer mock project type from prompt content ────────────────
            prompt_lower = user_prompt.lower()

            if any(t in prompt_lower for t in ("tutorial", "course", "exercise", "learn")):
                mock_type = "learning"
                mock_persona = "A learning repository with step-by-step coding exercises."
                mock_problem = "Developers need structured practice to cement new skills."
                mock_solution = "This repo provides guided exercises with increasing complexity."
            elif any(t in prompt_lower for t in ("demo", "showcase", "showroom", "sample-app")):
                mock_type = "demo"
                mock_persona = "A showcase demonstrating the core capabilities of the system."
                mock_problem = "Stakeholders need a quick way to see the tool in action."
                mock_solution = "This demo runs in one command and shows the full workflow end-to-end."
            elif any(t in prompt_lower for t in ("proof of concept", "poc", "experiment", "prototype")):
                mock_type = "poc"
                mock_persona = "An experimental proof-of-concept exploring a novel approach."
                mock_problem = "The feasibility of this approach was unproven."
                mock_solution = "This PoC validates the core idea with a minimal working implementation."
            elif any(t in prompt_lower for t in ("fastapi", "flask", "@app.route", "express", "router")):
                mock_type = "api"
                mock_persona = "A REST API service exposing structured endpoints."
                mock_problem = "Clients needed a reliable interface to consume backend data."
                mock_solution = "This API provides typed endpoints with clear request/response contracts."
            elif any(t in prompt_lower for t in ("argparse", "click", "typer", "sys.argv", "commander")):
                mock_type = "cli"
                mock_persona = "A command-line tool for developer productivity."
                mock_problem = "Repetitive terminal tasks required manual intervention each time."
                mock_solution = "This CLI automates those tasks behind simple, memorable commands."
            elif any(t in prompt_lower for t in ("pypi", "npm publish", "cargo publish", "setup.py", "pyproject")):
                mock_type = "library"
                mock_persona = "A reusable library that can be imported into other projects."
                mock_problem = "Developers needed to solve this problem repeatedly across projects."
                mock_solution = "This library encapsulates the solution as a clean, importable package."
            else:
                mock_type = "application"
                mock_persona = "An agentic multi-agent CLI and web tool for README generation."
                mock_problem = "Writing READMEs manually is repetitive and results in generic docs."
                mock_solution = "It automates analysis and formatting through a multi-agent framework."

            mock_analysis = {
                "project_name": "MockProject",
                "project_type": mock_type,
                "project_type_reason": f"Detected signals in the codebase match a '{mock_type}' project.",
                "project_maturity": "development",
                "classification": {
                    "primary_intent": mock_type,
                    "delivery_surfaces": ["package", "cli"] if mock_type == "cli" else ["ui", "api"] if mock_type == "api" else ["package"],
                    "confidence": 0.75,
                },
                "tech_stack": ["Python", "Rich", "Pytest"],
                "project_persona": mock_persona,
                "problem_statement": mock_problem,
                "solution_narrative": mock_solution,
                "key_features": [
                    {"name": "Core Feature A", "description": "The primary capability of this project.", "category": "Core"},
                    {"name": "Integration Layer", "description": "Connects to external services via a clean abstraction.", "category": "Integration"},
                ],
                "api_endpoints": [
                    {"method": "POST", "path": "/api/analyze", "description": "Analyze a repository and return structured results."},
                    {"method": "POST", "path": "/api/generate", "description": "Generate a README from analysis context."},
                ] if mock_type in ("api", "application") else [],
                "config_variables": [
                    {"name": "API_KEY", "description": "Authentication key for the LLM provider.", "required": True, "default": ""},
                    {"name": "MODEL_NAME", "description": "Override the default model selection.", "required": False, "default": "auto"},
                ],
                "cli_commands": [
                    {"command": "readme-forge --path .", "description": "Generate README for the current directory."},
                    {"command": "readme-forge --path . --instant", "description": "Skip interactive mode and generate immediately."},
                ] if mock_type in ("cli", "application") else [],
                "data_models": [
                    {"name": "ScanResults", "fields": ["tree", "configs", "code_context", "test_signals"], "description": "Output of the ReaderAgent codebase scan."},
                ],
                "installation_commands": [
                    {"step": "1", "command": "git clone https://github.com/user/project.git", "description": "Clone the repository."},
                    {"step": "2", "command": "cd project && pip install -r requirements.txt", "description": "Install dependencies."},
                    {"step": "3", "command": "cp .env.example .env && nano .env", "description": "Configure environment variables."},
                ],
                "external_services": ["Gemini API", "OpenAI API"],
                "test_coverage": {
                    "has_tests": True,
                    "framework": "pytest",
                    "test_count": 22,
                    "description": "Unit tests covering agent contracts, analyzer fallback, drift detection, and writer coercion.",
                },
                "architecture_layers": [
                    {"layer": "CLI / Web Entrypoint", "files": ["main.py", "server.py"], "responsibility": "Argument parsing and HTTP request handling."},
                    {"layer": "Agent Orchestrator", "files": ["readme_forge/agents/orchestrator.py"], "responsibility": "Coordinates all agents in sequence."},
                    {"layer": "Reader Agent", "files": ["readme_forge/agents/reader.py"], "responsibility": "Scans local and remote codebases."},
                    {"layer": "Analyzer Agent", "files": ["readme_forge/agents/analyzer.py"], "responsibility": "Extracts structured facts via LLM."},
                    {"layer": "Writer Agent", "files": ["readme_forge/agents/writer.py"], "responsibility": "Generates polished README markdown."},
                ],
                "improvements": [
                    {"id": "1", "title": "Add architecture diagram", "description": "A visual flow would clarify component relationships.", "type": "Visual"},
                    {"id": "2", "title": "Document configuration variables", "description": "Environment variables are undocumented in the README.", "type": "Configuration"},
                ],
                "connections": [
                    {"from": "CLI Entrypoint", "to": "Orchestrator", "relationship": "invokes", "layer": "orchestration"},
                    {"from": "Orchestrator", "to": "Reader Agent", "relationship": "scans codebase", "layer": "orchestration"},
                    {"from": "Reader Agent", "to": "Analyzer Agent", "relationship": "provides scan results", "layer": "data"},
                    {"from": "Analyzer Agent", "to": "LLM Client", "relationship": "requests analysis", "layer": "integration"},
                    {"from": "Analyzer Agent", "to": "Writer Agent", "relationship": "passes analysis", "layer": "orchestration"},
                    {"from": "Writer Agent", "to": "README.md", "relationship": "writes output", "layer": "data"},
                ],
            }
            return json.dumps(mock_analysis, indent=2)

        # ── README generation mock ─────────────────────────────────────────
        if "generate" in user_prompt.lower() or "readme" in user_prompt.lower():
            return """# MockProject

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

> A demonstration README generated by the mock LLM provider.

## The Problem

Manual documentation is time-consuming and often falls behind the actual codebase.

## The Solution

This project automates documentation by analysing the repository structure and generating
a tailored README using a multi-agent pipeline.

## How It Works

```mermaid
flowchart TD
    A["CLI / Web"] --> B["Orchestrator"]
    B --> C["Reader Agent"]
    C --> D["Analyzer Agent"]
    D --> E["Writer Agent"]
    E --> F["README.md"]
```

1. **Step 1 — Ingest**: The CLI or web server receives a repository path or URL.
2. **Step 2 — Scan**: `ReaderAgent` walks the directory tree and extracts source files.
3. **Step 3 — Analyze**: `AnalyzerAgent` sends context to the LLM and receives structured JSON.
4. **Step 4 — Write**: `WriterAgent` builds the final README from the analysis contract.

## Installation

```shell
git clone https://github.com/user/project.git
cd project
pip install -r requirements.txt
cp .env.example .env
```

## Quick Start

```shell
readme-forge --path .
```

## Configuration

| Variable | Description | Required | Default |
|---|---|---|---|
| `API_KEY` | LLM provider API key | Yes | — |
| `MODEL_NAME` | Model override | No | auto |

## Contributing & License

MIT License — contributions welcome via pull request.
"""

        return "Mock Response: Operation completed successfully."

