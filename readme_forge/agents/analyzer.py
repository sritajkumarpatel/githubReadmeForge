import json
from readme_forge.llm import LLMClient

class AnalyzerAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def analyze(self, scan_results):
        """Analyzes the scan results from the ReaderAgent and extracts structural facts, improvements, and connections."""
        system_prompt = (
            "You are an expert AI software architect and Analyzer Agent.\n"
            "Your task is to analyze the contents of a codebase scan and produce a structured JSON report.\n"
            "You MUST respond ONLY with a valid JSON object matching the schema below. Do not wrap in markdown code blocks like ```json.\n"
            "\n"
            "JSON Response Schema:\n"
            "{\n"
            "  \"tech_stack\": [\"List\", \"of\", \"languages/frameworks/major dependencies\"],\n"
            "  \"project_persona\": \"Short, descriptive, high-level summary of what this project does and who it is for.\",\n"
            "  \"improvements\": [\n"
            "    {\n"
            "      \"id\": \"1\",\n"
            "      \"title\": \"Short title of the improvement\",\n"
            "      \"description\": \"Detailed explanation of what is missing or can be improved (e.g., bad README, missing tech stack, no CLI guide, no API docs)\",\n"
            "      \"type\": \"Category of improvement (e.g. Structure, Examples, Configuration, Badges)\"\n"
            "    }\n"
            "  ],\n"
            "  \"connections\": [\n"
            "    {\n"
            "      \"from\": \"Source component or layer\",\n"
            "      \"to\": \"Destination component or layer\",\n"
            "      \"relationship\": \"Brief action or explanation of link (optional)\"\n"
            "    }\n"
            "  ]\n"
            "}"
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

        user_prompt = (
            f"Here is the directory tree of the repository:\n"
            f"```\n{tree_text}\n```\n\n"
            f"Here is the existing README content (if any):\n"
            f"```markdown\n{existing_readme}\n```\n\n"
            f"Here are details from project configuration files:\n"
            f"{configs_text}\n\n"
            f"Here are snippets from primary entry point code files:\n"
            f"{code_context_text}\n\n"
            f"Please analyze these resources and return the JSON analysis."
        )

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
                "tech_stack": ["Detected from files"],
                "project_persona": "A software codebase project",
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
