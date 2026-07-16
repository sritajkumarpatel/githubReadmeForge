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
        """Simulates LLM responses based on keywords in the prompt for demo/testing purposes."""
        # Detect if it's the analyzer requesting JSON structure
        if "improvement points" in user_prompt.lower() or "list_improvements" in system_prompt.lower() or response_format_json:
            mock_analysis = {
                "tech_stack": ["Python", "Rich CLI", "Git API", "LLMs"],
                "project_persona": "An agentic terminal developer utility",
                "improvements": [
                    {
                        "id": "1",
                        "title": "Missing visual architectural layout",
                        "description": "The current codebase has no visual representation showing how the CLI, agents, and LLMs interact.",
                        "type": "Structure"
                    },
                    {
                        "id": "2",
                        "title": "Inconsistent configuration documentation",
                        "description": "It is not clear how to set up LLM API keys or local Ollama endpoints.",
                        "type": "Configuration"
                    },
                    {
                        "id": "3",
                        "title": "Lack of quick start/usage examples",
                        "description": "No concrete example commands or visual showcase showing how simple it is to generate markdown.",
                        "type": "Examples"
                    }
                ],
                "connections": [
                    {"from": "CLI Entrypoint", "to": "Orchestrator"},
                    {"from": "Orchestrator", "to": "Reader Agent"},
                    {"from": "Orchestrator", "to": "Analyzer Agent"},
                    {"from": "Orchestrator", "to": "Writer Agent"},
                    {"from": "Analyzer Agent", "to": "LLM Wrapper"},
                    {"from": "Writer Agent", "to": "LLM Wrapper"}
                ]
            }
            return json.dumps(mock_analysis, indent=2)

        # Detect if it's the writer requesting README generation
        if "generate" in user_prompt.lower() or "readme" in user_prompt.lower():
            return """# 🛠️ githubReadmeForge

[![GitHub License](https://img.shields.io/github/license/user/repo?style=flat-square)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue?style=flat-square)](https://www.python.org/)
[![Multi-Agentic](https://img.shields.io/badge/architecture-multi--agentic-purple?style=flat-square)](#architecture)

A terminal-based CLI tool that uses a multi-agent orchestration framework to analyze codebases and forge consistent, visually structured, and example-rich `README.md` files.

---

## 🎯 Features

- **Multi-Agent Orchestration**: Separate specialized agents for reading files, analyzing architecture, and compiling markdown.
- **Pluggable LLM Providers**: Support for Gemini, OpenAI, Claude, and local Ollama models.
- **Interactive & Instant Modes**: Get a quick automated draft or review improvement points step-by-step.
- **Rich Visuals**: Automatic integration of Mermaid.js architecture diagrams and repository layout visualizers.

---

## 🏗️ Architecture

```mermaid
graph TD
    User([User CLI Input]) --> CLI[CLI Entrypoint: cli.py]
    CLI --> LLM[LLM Client Wrapper: llm.py]
    CLI --> Orch[Agent Orchestrator: orchestrator.py]
    
    Orch --> Reader[Reader Agent: reader.py]
    Orch --> Analyzer[Analyzer Agent: analyzer.py]
    Orch --> Writer[Writer Agent: writer.py]
```

---

## 🚀 Getting Started

### Installation

```bash
git clone https://github.com/user/githubReadmeForge.git
cd githubReadmeForge
pip install -r requirements.txt
```

### Usage

Run the tool in interactive mode on your repository:
```bash
python main.py --path .
```

For instant mode without questions:
```bash
python main.py --path . --instant
```

---

## ⚙️ Configuration

<details>
<summary><b>API Credentials Setup</b></summary>

Set up environment variables for your chosen LLM provider:

```bash
# For Gemini (Default)
export GEMINI_API_KEY="your-gemini-key"

# For OpenAI
export OPENAI_API_KEY="your-openai-key"

# For Anthropic Claude
export ANTHROPIC_API_KEY="your-claude-key"

# For local Ollama
export README_FORGE_PROVIDER="ollama"
export OLLAMA_HOST="http://localhost:11434"
```
</details>

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
"""

        return "Mock Response: Operation completed successfully."
