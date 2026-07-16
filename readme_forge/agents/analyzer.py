import json
from readme_forge.llm import LLMClient

class AnalyzerAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def analyze(self, scan_results):
        """Analyzes the scan results from the ReaderAgent and extracts deep structural facts, features, config, and architecture."""
        system_prompt = (
            "You are an expert AI software architect and Analyzer Agent.\n"
            "Your task is to deeply analyze the contents of a codebase scan and produce a comprehensive structured JSON report.\n"
            "You MUST respond ONLY with a valid JSON object matching the schema below. Do not wrap in markdown code blocks like ```json.\n"
            "\n"
            "CRITICAL: Do NOT produce shallow, generic analysis. Extract SPECIFIC details from the actual code files.\n"
            "Read the source code snippets carefully to understand what the project actually does.\n"
            "\n"
            "JSON Response Schema:\n"
            "{\n"
            "  \"project_type\": \"One of: learning, poc, library, application, cli, api, minimal. Choose the most accurate type.\",\n"
            "  \"project_type_reason\": \"Brief explanation of why this type was selected.\",\n"
            "  \"project_maturity\": \"One of: production, development, poc, unknown. Be honest about the project's current state.\",\n"
            "  \"tech_stack\": [\"List of specific languages, frameworks, and major dependencies detected\"],\n"
            "  \"project_persona\": \"A clear, compelling 1-2 sentence description of what this project does and who it is for.\",\n"
            "  \"problem_statement\": \"What specific pain point or problem does this project solve? Write 2-3 sentences describing the problem from the user's perspective.\",\n"
            "  \"solution_narrative\": \"How does this project solve the problem? Write 2-3 sentences describing the approach and key differentiators.\",\n"
            "  \"key_features\": [\n"
            "    {\n"
            "      \"name\": \"Feature name\",\n"
            "      \"description\": \"What this feature does and why it matters\",\n"
            "      \"category\": \"Category (e.g. Core, Integration, Developer Experience, Security)\"\n"
            "    }\n"
            "  ],\n"
            "  \"api_endpoints\": [\n"
            "    {\n"
            "      \"method\": \"HTTP method (GET/POST/PUT/DELETE)\",\n"
            "      \"path\": \"/api/endpoint\",\n"
            "      \"description\": \"What this endpoint does\"\n"
            "    }\n"
            "  ],\n"
            "  \"config_variables\": [\n"
            "    {\n"
            "      \"name\": \"VARIABLE_NAME\",\n"
            "      \"description\": \"What this variable controls\",\n"
            "      \"required\": true,\n"
            "      \"default\": \"default value or empty string\"\n"
            "    }\n"
            "  ],\n"
            "  \"cli_commands\": [\n"
            "    {\n"
            "      \"command\": \"example command\",\n"
            "      \"description\": \"What it does\"\n"
            "    }\n"
            "  ],\n"
            "  \"improvements\": [\n"
            "    {\n"
            "      \"id\": \"1\",\n"
            "      \"title\": \"Short title of the improvement\",\n"
            "      \"description\": \"Detailed explanation of what is missing or can be improved\",\n"
            "      \"type\": \"Category of improvement (e.g. Structure, Examples, Configuration, Badges)\"\n"
            "    }\n"
            "  ],\n"
            "  \"connections\": [\n"
            "    {\n"
            "      \"from\": \"Source component or layer\",\n"
            "      \"to\": \"Destination component or layer\",\n"
            "      \"relationship\": \"Brief action or explanation of link\"\n"
            "    }\n"
            "  ]\n"
            "}\n"
            "\n"
            "PROJECT TYPE GUIDELINES:\n"
            "- learning: Tutorial projects, starter templates, educational code. Keep README simple and focused on learning.\n"
            "- poc: Proof-of-concept or prototype projects. README should be honest about experimental status and list what's working vs planned.\n"
            "- library: Reusable packages/modules published to npm/pypi/crates.io. Focus on API reference, installation, and usage examples.\n"
            "- application: Full web/desktop applications with multiple features. Comprehensive docs with all sections.\n"
            "- cli: Command-line tools. Focus on commands, flags, and usage examples.\n"
            "- api: Backend API services. Focus on endpoints, authentication, and request/response examples.\n"
            "- minimal: Small utility scripts or single-file projects. Concise README is sufficient.\n"
            "\n"
            "PROJECT MATURITY CLASSIFICATION:\n"
            "Classify the project maturity honestly:\n"
            "- production: Stable, well-tested, production-ready. Has CI/CD, tests, documentation.\n"
            "- development: Active development, may have some rough edges. Has basic functionality working.\n"
            "- poc: Proof-of-concept, early prototype, or experiment. May be incomplete or non-functional.\n"
            "- unknown: Unable to determine maturity from available information.\n"
            "\n"
            "IMPORTANT RULES:\n"
            "- key_features: Extract at least 3-5 real features from the code. Do NOT invent features that aren't in the codebase.\n"
            "- api_endpoints: Only include if the project has HTTP/API routes. Leave as empty array if not applicable.\n"
            "- config_variables: Extract from .env files, environment variable reads in code (os.getenv, process.env), and CLI argument parsers.\n"
            "- cli_commands: Extract from argparse, click, commander, or similar CLI framework usage. Leave as empty array if not applicable.\n"
            "- problem_statement: Infer the pain point from what the tool does. Think about why someone would need this.\n"
            "- connections: Map the actual architectural flow between real components/files, not generic patterns.\n"
            "\n"
            "EXTRACT SPECIFICS - DO NOT USE GENERIC DESCRIPTIONS:\n"
            "- tech_stack: List SPECIFIC frameworks, libraries, and tools (e.g., 'FastMCP', 'UV', 'Pydantic', 'MCP Inspector', 'Uvicorn'). Do NOT just say 'Python' when the project uses 'FastMCP' or 'Streamable HTTP'.\n"
            "- project_persona: Be specific about what the project actually does. 'A learning project for MCP servers' is better than 'A software application'.\n"
            "- key_features: Describe what the specific code does. 'Weather data fetching via MCP protocol' is better than 'Data retrieval feature'.\n"
        )

        # Prepare user prompt with codebase data
        tree_text = scan_results.get("tree", "")
        configs_text = ""
        for fn, contents in scan_results.get("configs", {}).items():
            configs_text += f"--- FILE: {fn} ---\n{contents}\n\n"
            
        code_context_text = ""
        for path, contents in scan_results.get("code_context", {}).items():
            code_context_text += f"--- FILE: {path} ---\n{contents}\n\n"

        existing_readme = scan_results.get("existing_readme", "")
        
        narrative_hints_text = ""
        for hint in scan_results.get("narrative_hints", []):
            narrative_hints_text += f"- {hint}\n"

        user_prompt = (
            f"Here is the directory tree of the repository:\n"
            f"```\n{tree_text}\n```\n\n"
            f"Here is the existing README content (if any):\n"
            f"```markdown\n{existing_readme}\n```\n\n"
            f"Here are details from project configuration files:\n"
            f"{configs_text}\n\n"
            f"Here are snippets from primary source code files:\n"
            f"{code_context_text}\n\n"
        )
        
        if narrative_hints_text:
            user_prompt += (
                f"Here are narrative hints extracted from the project metadata:\n"
                f"{narrative_hints_text}\n\n"
            )
        
        user_prompt += "Please analyze these resources and return the comprehensive JSON analysis."

        raw_response = self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format_json=True
        )

        # Clean response if the model wrapped it in markdown code blocks despite instructions
        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            # Strip first line
            lines = clean_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_response = "\n".join(lines).strip()

        try:
            analysis_data = json.loads(clean_response)
            return analysis_data
        except Exception as e:
            # Return basic fallback structure in case LLM outputs invalid JSON
            print(f"[Analyzer] Warning: Failed to parse LLM analysis JSON: {e}")
            return {
                "project_type": "application",
                "project_type_reason": "Default classification based on available information.",
                "project_maturity": "unknown",
                "tech_stack": ["Detected from files"],
                "project_persona": "A software codebase project",
                "problem_statement": "This project addresses a specific developer need.",
                "solution_narrative": "It provides a solution through its implementation.",
                "key_features": [],
                "api_endpoints": [],
                "config_variables": [],
                "cli_commands": [],
                "improvements": [
                    {
                        "id": "1",
                        "title": "README enhancement required",
                        "description": "Standardize README format and structure, add examples and architecture diagrams.",
                        "type": "General"
                    }
                ],
                "connections": []
            }
