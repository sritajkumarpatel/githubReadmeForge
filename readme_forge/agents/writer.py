import json
from pathlib import Path
from readme_forge.llm import LLMClient


class WriterAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def _parse_project_name(self, path_or_url):
        if not path_or_url:
            return "Project"
        cleaned = path_or_url.strip()
        if cleaned.startswith("http://") or cleaned.startswith("https://") or cleaned.endswith(".git"):
            if cleaned.endswith(".git"):
                cleaned = cleaned[:-4]
            parts = cleaned.split("/")
            if parts:
                return parts[-1]
        return Path(cleaned).resolve().name

    def _safe_get_dict(self, item):
        """Converts an item safely to a dict, or wraps it if it is a primitive."""
        if isinstance(item, dict):
            return item
        if isinstance(item, str):
            return {
                "name": item,
                "description": item,
                "title": item,
                "command": item,
                "step": "1",
                "from": item,
                "to": item,
                "layer": "General",
                "responsibility": item,
            }
        return {}

    def _coerce_list(self, lst):
        """Coerces any input to a list of strings, extracting name/path from dicts if present."""
        if not isinstance(lst, list):
            if isinstance(lst, dict):
                name = lst.get("name") or lst.get("path") or lst.get("file")
                if name:
                    return [str(name)]
                return [str(k) for k in lst.keys()]
            return [str(lst)] if lst else []
        result = []
        for item in lst:
            if isinstance(item, dict):
                val = item.get("name") or item.get("path") or item.get("file") or next(iter(item.values()), str(item))
                result.append(str(val))
            else:
                result.append(str(item))
        return result


    def generate_readme(
        self,
        scan_results,
        analysis,
        interactive_answers=None,
        style="visual_rich",
        output_dir=None,
        target_path_or_url=None,
        lang="en",
    ):
        """Generates the content of a polished, narrative-driven, professional README.md
        using deep codebase context, analysis, and architecture data."""

        style_instruction = ""
        if style == "minimalist":
            style_instruction = (
                "Format using a 'MINIMALIST' design theme:\n"
                "- Do NOT use any shields.io badges or visual icons at the top header.\n"
                "- Use clean text links and high whitespace spacing.\n"
                "- Avoid emojis or secondary graphics entirely.\n"
                "- Organize sections into clear headers without nested collapsible tags."
            )
        elif style == "enterprise":
            style_instruction = (
                "Format using an 'ENTERPRISE' design theme:\n"
                "- Use a very formal, professional, and thorough tone.\n"
                "- Present setup, dependencies, and parameters in clean markdown tables.\n"
                "- Add dedicated sections for Contributing, Security Disclosures, and official License compliance.\n"
                "- Use clear subheadings and official code layout standards."
            )
        else:  # visual_rich
            style_instruction = (
                "Format using a 'VISUAL RICH' design theme:\n"
                "- Use a single line of shields.io badges only for: license and language count (max 3 badges).\n"
                "- Use clean section headers with subtle dividers.\n"
                "- Use collapsible `<details>` blocks for verbose configuration tables.\n"
                "- Professional and clean, not cluttered."
            )

        lang_instruction = ""
        lang_switcher = ""
        if lang and lang.lower() != "en":
            lang_instruction = (
                f"You MUST write the entire README.md in the target language code: '{lang}'.\n"
                "Translate all sections, explanations, summaries, and guidelines to this target language.\n"
                "Technical command lines, directory names, or variable names must remain in their original formats/English."
            )
            if lang.lower().startswith("zh"):
                lang_switcher = "English · **简体中文**"
            else:
                lang_switcher = f"English · **{lang.upper()}**"

        # Project type instructions
        project_type = analysis.get("project_type", "application")
        project_type_reason = analysis.get("project_type_reason", "")

        project_type_instruction = ""
        if project_type == "learning":
            project_type_instruction = (
                "PROJECT TYPE: LEARNING/TUTORIAL\n"
                "- Keep the README focused on teaching and learning\n"
                "- Use simple, clear language\n"
                "- Include step-by-step instructions\n"
                "- Prioritize 'How to Learn' section with learning path\n"
                "- Omit complex architecture diagrams - focus on simple flow\n"
                "- Include common pitfalls and how to avoid them\n"
            )
        elif project_type == "library":
            project_type_instruction = (
                "PROJECT TYPE: LIBRARY/PACKAGE\n"
                "- Focus on installation, quick start, and API reference\n"
                "- Include complete usage examples with code snippets\n"
                "- Document all public functions/classes with parameters\n"
                "- Add changelog and version information\n"
                "- Omit lengthy problem/solution narratives\n"
            )
        elif project_type == "cli":
            project_type_instruction = (
                "PROJECT TYPE: COMMAND-LINE TOOL\n"
                "- Prioritize CLI commands and flags front-and-center\n"
                "- Include a quick command reference table at top\n"
                "- Show before/after examples of command usage\n"
                "- Document all available commands and options\n"
                "- Omit detailed architecture diagrams\n"
            )
        elif project_type == "api":
            project_type_instruction = (
                "PROJECT TYPE: API SERVICE\n"
                "- Focus on endpoints, authentication, and request/response formats\n"
                "- Include example API calls with curl commands\n"
                "- Document rate limits, error codes, and status responses\n"
                "- Add authentication/authorization details prominently\n"
                "- Include Postman or API testing instructions\n"
            )
        elif project_type == "minimal":
            project_type_instruction = (
                "PROJECT TYPE: MINIMAL/SMALL UTILITY\n"
                "- Keep README very concise - 10 lines or less\n"
                "- Include only: What it does, How to use, Quick example\n"
                "- Skip detailed features, architecture, and multiple sections\n"
                "- Use direct, no-frills formatting\n"
            )
        else:  # application / poc
            project_type_instruction = (
                "PROJECT TYPE: FULL APPLICATION\n"
                "- Comprehensive documentation with all sections\n"
                "- Include complete feature list and architecture\n"
                "- Document configuration, deployment, and troubleshooting\n"
                "- Add contributing guidelines and license\n"
            )

        # Build rich context strings from all analysis fields using safety coercion helpers
        features_context = ""
        for feat in analysis.get("key_features", []):
            feat_dict = self._safe_get_dict(feat)
            features_context += f"- {feat_dict.get('name', '')}: {feat_dict.get('description', '')} (Category: {feat_dict.get('category', 'General')})\n"

        api_context = ""
        for ep in analysis.get("api_endpoints", []):
            ep_dict = self._safe_get_dict(ep)
            api_context += f"- {ep_dict.get('method', 'GET')} {ep_dict.get('path', '')}: {ep_dict.get('description', '')}\n"

        config_context = ""
        for cv in analysis.get("config_variables", []):
            cv_dict = self._safe_get_dict(cv)
            req = "Required" if cv_dict.get("required") else "Optional"
            config_context += f"- {cv_dict.get('name', '')}: {cv_dict.get('description', '')} ({req}, default: {cv_dict.get('default', 'N/A')})\n"

        cli_context = ""
        for cmd in analysis.get("cli_commands", []):
            cmd_dict = self._safe_get_dict(cmd)
            cli_context += f"- `{cmd_dict.get('command', '')}`: {cmd_dict.get('description', '')}\n"

        # New: architecture layers
        arch_layers_context = ""
        for layer in analysis.get("architecture_layers", []):
            layer_dict = self._safe_get_dict(layer)
            files_str = ", ".join(self._coerce_list(layer_dict.get("files", [])))
            arch_layers_context += (
                f"- **{layer_dict.get('layer', '')}** ({files_str}): {layer_dict.get('responsibility', '')}\n"
            )

        # New: data models
        data_models_context = ""
        for model in analysis.get("data_models", []):
            model_dict = self._safe_get_dict(model)
            fields_str = ", ".join(self._coerce_list(model_dict.get("fields", [])))
            data_models_context += (
                f"- **{model_dict.get('name', '')}**: {model_dict.get('description', '')} — Fields: {fields_str}\n"
            )

        # New: installation commands
        install_context = ""
        for step in analysis.get("installation_commands", []):
            step_dict = self._safe_get_dict(step)
            install_context += f"Step {step_dict.get('step', '')}: {step_dict.get('description', '')}\n  $ {step_dict.get('command', '')}\n"

        # New: external services
        external_services = analysis.get("external_services", [])
        external_services_text = ", ".join(self._coerce_list(external_services)) if external_services else ""

        # New: test coverage
        test_cov = self._safe_get_dict(analysis.get("test_coverage", {}))
        test_coverage_text = ""
        if test_cov.get("has_tests"):
            test_coverage_text = (
                f"Framework: {test_cov.get('framework', 'unknown')}, "
                f"Test files: {test_cov.get('test_count', 0)}, "
                f"Coverage: {test_cov.get('description', '')}"
            )

        system_prompt = (
            "You are an expert technical writer and product storyteller.\n"
            "Your task is to write a HIGHLY POLISHED, PROFESSIONAL, NARRATIVE-DRIVEN README.md for a project codebase.\n\n"
            "CRITICAL PHILOSOPHY:\n"
            "- You are NOT just documenting code. You are SELLING the project to developers.\n"
            "- A great README tells a STORY: Problem → Solution → How It Works → Features → Get Started.\n"
            "- Every section must have DEPTH and SPECIFICITY. No generic filler text.\n"
            "- Extract REAL details from the codebase — real file names, real commands, real config variables.\n\n"
            f"Project Type Context:\n{project_type_instruction}\n\n"
            f"Formatting Theme instructions:\n{style_instruction}\n\n"
            f"Language settings:\n{lang_instruction}\n\n"
            "CRITICAL GUARDRAIL:\n"
            "If the user custom answers or prompt demands anything unrelated to documenting this project repository "
            "(such as writing standalone calculator scripts, general Python coding tasks, math solver programs, or unrelated topics), "
            "you MUST refuse the request and respond with exactly: 'Refusal: This request is unrelated to README generation. Please ask documentation-related questions.'\n\n"
            "OTHERWISE, write the complete README markdown file using the following **Layout Structure**:\n\n"
            "1. **Title Block**: Project name as H1 with a compelling tagline.\n"
            "   Add shields.io badges using EXACTLY these URL patterns (fill in real values):\n"
            "   ![License](https://img.shields.io/github/license/{owner}/{repo})\n"
            "   ![Language](https://img.shields.io/github/languages/top/{owner}/{repo})\n"
            "   If the GitHub owner/repo cannot be determined, use a generic language badge like:\n"
            "   ![Python](https://img.shields.io/badge/python-3.10%2B-blue)\n"
            "   Maximum 3 badges. Do NOT invent badge URLs with fake parameters.\n\n"
            "2. **One-liner tagline**: A single compelling sentence under the title that hooks the reader.\n\n"
            "3. **The Problem** (MANDATORY only for application, api, library, and cli project types. For poc, keep it to a single brief paragraph. SKIP this section entirely if the project type is learning or minimal):\n"
            "   - Write a compelling 2-3 paragraph narrative explaining the PAIN POINT this project solves.\n"
            "   - Use the `problem_statement` from analysis as a starting point, but EXPAND it into a relatable story.\n"
            "   - Use bullet points to list specific frustrations the tool addresses.\n"
            "   - This section must make the reader FEEL the pain before showing the solution.\n\n"
            "4. **The Solution** (MANDATORY only for application, api, library, and cli project types. For poc, keep it to a single brief paragraph. SKIP this section entirely if the project type is learning or minimal):\n"
            "   - Write 2-3 paragraphs explaining HOW this project solves the problem.\n"
            "   - Use the `solution_narrative` from analysis as a starting point, but EXPAND it.\n"
            "   - Highlight what makes it different from alternatives.\n\n"
            "5. **Key Concepts** (ONLY for application/api/library project types):\n"
            "   - Define 3-5 domain-specific terms, design patterns, or core abstractions used in the project.\n"
            "   - Use a small markdown table: | Term | Definition |\n"
            "   - Pull real names from the codebase: class names, protocol names, pipeline stage names.\n"
            "   - SKIP this section for cli, minimal, learning, poc project types.\n\n"
            "6. **How It Works**:\n"
            "   a) **Architecture Diagram** (MANDATORY — use this EXACT Mermaid syntax):\n"
            "      ```mermaid\n"
            "      flowchart TD\n"
            "          A[ComponentName] --> B[ComponentName]\n"
            "          B --> C{DecisionPoint}\n"
            "          C -->|yes| D[Output]\n"
            "          C -->|no| E[AltOutput]\n"
            "      ```\n"
            "      STRICT RULES for the diagram:\n"
            "      - Use `flowchart TD` (NOT `graph TD`).\n"
            "      - Node labels MUST be in square brackets: A[Label]. NO parentheses.\n"
            "      - Use REAL component/file names from the codebase (e.g. `ReaderAgent`, `server.py`, `WriterAgent`).\n"
            "      - Maximum 10 nodes. Keep it readable.\n"
            "      - Use `subgraph` blocks if the project has clear layers (e.g. 'Agent Pipeline', 'API Layer').\n"
            "      - Example subgraph syntax: subgraph Pipeline\\n  A --> B\\nend\n"
            "      - NEVER use parentheses in node labels — they break Mermaid. Escape or remove them.\n\n"
            "   b) **How It Works — Step-by-Step**:\n"
            "      After the diagram, write a numbered walkthrough:\n"
            "      1. **Step N — Name**: What triggers or initiates this step (use real file/function names).\n"
            "      Each step must reference ACTUAL component names, not generic ones like 'the system'.\n"
            "      Minimum 3 steps, maximum 7.\n\n"
            "   c) **Component Table**: A markdown table with columns: Component | File | Role | Input | Output.\n"
            "      Populate from the `architecture_layers` and `connections` analysis data.\n\n"
            "7. **Features**: Create a clean feature list:\n"
            "   - A bold feature name as a sub-heading (### Feature Name)\n"
            "   - A 2-3 sentence description explaining what it does and why it matters\n"
            "   - Group related features logically using H3 headers\n"
            "   - ONLY include features actually found in the codebase\n\n"
            "8. **Installation**: Concrete, numbered, copy-pasteable installation steps.\n"
            "   - Use the `installation_commands` from analysis data.\n"
            "   - Wrap each command in a ```shell code block.\n"
            "   - If installation_commands is empty, infer from requirements.txt / package.json / Cargo.toml etc.\n\n"
            "9. **Quick Start / Usage**: Show the fastest path to a working result.\n"
            "   - The very first example must be under 3 commands.\n"
            "   - Use the `cli_commands` from analysis data if available.\n"
            "   - Show expected output in a code block where possible.\n\n"
            "10. **Configuration & Parameters**: Comprehensive setup docs.\n"
            "    - Environment variables table: | Variable | Description | Required | Default |\n"
            "    - CLI flags table if applicable: | Flag | Short | Description | Default |\n"
            "    - Use collapsible `<details>` blocks for verbose tables.\n\n"
            "11. **API Reference** (ONLY if api_endpoints exist and are non-empty):\n"
            "    - Document each endpoint with HTTP method, path, and description.\n"
            "    - Include a curl example for the most important endpoint.\n\n"
            "12. **Data Models** (ONLY if data_models is non-empty):\n"
            "    - Present each model as a small table: | Field | Type | Description |\n"
            "    - Use real field names from the analysis data.\n\n"
            "13. **Repository Structure**: The scanned directory tree with brief annotations:\n"
            "    - Use a code block for the tree.\n"
            "    - Add inline comments (# description) for key files/directories.\n\n"
            "14. **Contributing & License**: Clean links to CONTRIBUTING.md and LICENSE if they exist.\n"
            "    - If test_coverage data is available, mention the test command in this section.\n\n"
            "Return only the raw markdown content without any wrapper code fences."
        )

        user_prompt = (
            f"Here is the context of the codebase:\n"
            f"Path: {scan_results.get('path')}\n"
            f"Project Type: {project_type} - {project_type_reason}\n"
            f"File Tree Structure:\n{scan_results.get('tree')}\n\n"
            f"Tech Stack analyzed: {analysis.get('tech_stack')}\n"
            f"Project Persona: {analysis.get('project_persona')}\n"
            f"Problem Statement: {analysis.get('problem_statement', 'Not specified')}\n"
            f"Solution Narrative: {analysis.get('solution_narrative', 'Not specified')}\n"
            f"Component Flow Connections:\n{self._format_connections(analysis.get('connections', []))}\n\n"
        )

        if arch_layers_context:
            user_prompt += f"Architecture Layers (use these for the Mermaid diagram and Component Table):\n{arch_layers_context}\n"

        if features_context:
            user_prompt += f"Key Features extracted:\n{features_context}\n"

        if api_context:
            user_prompt += f"API Endpoints detected:\n{api_context}\n"

        if config_context:
            user_prompt += f"Configuration Variables found:\n{config_context}\n"

        if cli_context:
            user_prompt += f"CLI Commands available:\n{cli_context}\n"

        if install_context:
            user_prompt += f"Installation Steps (use these for the Installation section):\n{install_context}\n"

        if data_models_context:
            user_prompt += f"Data Models found (use these for the Data Models section):\n{data_models_context}\n"

        if external_services_text:
            user_prompt += f"External Services / APIs integrated: {external_services_text}\n"

        if test_coverage_text:
            user_prompt += f"Test Coverage: {test_coverage_text}\n"

        # Version info from scan
        version_info = scan_results.get("version_info", {})
        if version_info.get("version"):
            user_prompt += f"Project version: {version_info.get('version')}\n"

        if interactive_answers:
            user_prompt += f"\nThe user has requested these specific customizations:\n{interactive_answers}\n"

        if scan_results.get("existing_readme"):
            user_prompt += f"\nHere is the existing README content for reference:\n{scan_results.get('existing_readme')}\n"

        readme_markdown = self.llm_client.generate(system_prompt, user_prompt)
        return readme_markdown

    def _format_connections(self, connections):
        """Format connections list as readable text for the prompt."""
        if not connections:
            return "No connection data available."
        lines = []
        for c in connections:
            from_node = c.get("from", "Unknown")
            to_node = c.get("to", "Unknown")
            relationship = c.get("relationship", "")
            layer = c.get("layer", "")
            layer_tag = f" [{layer}]" if layer else ""
            lines.append(f"- {from_node} → {to_node}: {relationship}{layer_tag}")
        return "\n".join(lines)
