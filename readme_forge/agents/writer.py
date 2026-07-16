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

    def generate_showroom_html(self, readme_markdown, analysis):
        """Generates a premium glassmorphic Showroom HTML file that renders the README dynamically
        and includes rich visual tabs/animations."""

        escaped_readme = json.dumps(readme_markdown)[1:-1]

        tech_badges = ""
        for tech in self._coerce_list(analysis.get("tech_stack", []))[:6]:
            tech_badges += f'<span class="tech-badge">{tech}</span> '

        # Build Mermaid connections graph from connections data
        mermaid_connections = ["flowchart TD"]
        seen_nodes = set()
        for c in analysis.get("connections", []):
            c_dict = self._safe_get_dict(c)
            raw_from = c_dict.get("from", "")
            raw_to = c_dict.get("to", "")
            # Sanitize: replace spaces and special chars for node IDs
            id_from = raw_from.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
            id_to = raw_to.replace(" ", "_").replace("-", "_").replace(".", "_").replace("/", "_")
            if not id_from or not id_to:
                continue
            label_from = raw_from.replace('"', "'")
            label_to = raw_to.replace('"', "'")
            relationship = c_dict.get("relationship", "")[:30].replace('"', "'")

            if id_from not in seen_nodes:
                mermaid_connections.append(f'    {id_from}["{label_from}"]')
                seen_nodes.add(id_from)
            if id_to not in seen_nodes:
                mermaid_connections.append(f'    {id_to}["{label_to}"]')
                seen_nodes.add(id_to)

            if relationship:
                mermaid_connections.append(f'    {id_from} -->|"{relationship}"| {id_to}')
            else:
                mermaid_connections.append(f"    {id_from} --> {id_to}")

        mermaid_graph_str = "\n".join(mermaid_connections)

        # Build architecture layers panel
        arch_layers_html = ""
        for layer in analysis.get("architecture_layers", []):
            layer_dict = self._safe_get_dict(layer)
            files_str = ", ".join(f"<code>{f}</code>" for f in self._coerce_list(layer_dict.get("files", [])))
            arch_layers_html += (
                f'<div class="arch-layer">'
                f'<div class="arch-layer-name">{layer_dict.get("layer", "")}</div>'
                f'<div class="arch-layer-files">{files_str}</div>'
                f'<div class="arch-layer-desc">{layer_dict.get("responsibility", "")}</div>'
                f"</div>\n"
            )

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{analysis.get('project_persona', 'Project Showroom')}</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg-main: #f8fafc;
            --bg-glass: rgba(255, 255, 255, 0.7);
            --border-glass: rgba(0, 0, 0, 0.08);
            --text-primary: #0f172a;
            --text-secondary: #64748b;
            --text-muted: #94a3b8;
            --accent: #0369a1;
            --accent-light: rgba(3, 105, 161, 0.08);
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.05);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.08);
            --shadow-lg: 0 8px 30px rgba(0,0,0,0.12);
        }}

        * {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-main);
            background-image:
                radial-gradient(ellipse at 20% 0%, rgba(3, 105, 161, 0.03) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 100%, rgba(3, 105, 161, 0.03) 0%, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 3rem 2rem;
            line-height: 1.6;
        }}

        .container {{
            width: 100%;
            max-width: 1100px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }}

        header {{
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            padding: 2rem 2.5rem;
            box-shadow: var(--shadow-lg);
        }}

        h1 {{
            font-size: 2rem;
            font-weight: 800;
            color: var(--text-primary);
            margin-bottom: 0.5rem;
            letter-spacing: -0.02em;
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 1rem;
            line-height: 1.5;
            margin-bottom: 1.25rem;
        }}

        .tech-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .tech-badge {{
            background: var(--bg-main);
            border: 1px solid var(--border-glass);
            color: var(--text-secondary);
            padding: 0.35rem 0.75rem;
            border-radius: 6px;
            font-size: 0.8rem;
            font-weight: 500;
        }}

        main {{ display: grid; grid-template-columns: 1fr; gap: 2rem; }}

        .tabs-container {{
            background: var(--bg-glass);
            backdrop-filter: blur(20px);
            -webkit-backdrop-filter: blur(20px);
            border: 1px solid var(--border-glass);
            border-radius: 16px;
            box-shadow: var(--shadow-lg);
            overflow: hidden;
        }}

        .tab-bar {{
            display: flex;
            border-bottom: 1px solid var(--border-glass);
            background: rgba(255,255,255,0.5);
            padding: 0 1.5rem;
        }}

        .tab-btn {{
            background: none;
            border: none;
            color: var(--text-muted);
            padding: 1rem 1.25rem;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            transition: all 0.2s ease;
            position: relative;
            font-family: 'Outfit', sans-serif;
        }}

        .tab-btn:hover {{ color: var(--text-secondary); }}
        .tab-btn.active {{ color: var(--accent); }}
        .tab-btn.active::after {{
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 100%;
            height: 2px;
            background: var(--accent);
        }}

        .tab-content {{ padding: 2.5rem; display: none; }}
        .tab-content.active {{ display: block; }}

        /* Markdown styling */
        .markdown-body {{ line-height: 1.7; color: var(--text-primary); }}
        .markdown-body h1 {{
            font-size: 2rem; font-weight: 800; margin-bottom: 1rem;
            color: var(--text-primary); letter-spacing: -0.02em;
        }}
        .markdown-body h2 {{
            font-size: 1.5rem; font-weight: 600; margin-top: 2rem;
            margin-bottom: 1rem; border-bottom: 1px solid var(--border-glass);
            padding-bottom: 0.5rem; color: var(--text-primary);
        }}
        .markdown-body h3 {{
            font-size: 1.2rem; font-weight: 600; margin-top: 1.5rem;
            margin-bottom: 0.75rem; color: var(--text-primary);
        }}
        .markdown-body p {{ margin-bottom: 1rem; color: var(--text-secondary); }}
        .markdown-body ul, .markdown-body ol {{
            margin-left: 1.5rem; margin-bottom: 1rem; color: var(--text-secondary);
        }}
        .markdown-body li {{ margin-bottom: 0.4rem; }}
        .markdown-body a {{ color: var(--accent); text-decoration: none; }}
        .markdown-body a:hover {{ text-decoration: underline; }}
        .markdown-body pre {{
            background: #f1f5f9;
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            overflow-x: auto;
        }}
        .markdown-body code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.85rem;
        }}
        .markdown-body :not(pre) > code {{
            background: var(--bg-main);
            padding: 0.15rem 0.4rem;
            border-radius: 4px;
            font-size: 0.85em;
            border: 1px solid var(--border-glass);
        }}
        .markdown-body table {{
            width: 100%; border-collapse: collapse;
            margin-bottom: 1.5rem; font-size: 0.9rem;
        }}
        .markdown-body th, .markdown-body td {{
            border: 1px solid var(--border-glass);
            padding: 0.75rem 1rem; text-align: left;
        }}
        .markdown-body th {{
            background: var(--bg-main); font-weight: 600;
        }}
        .markdown-body blockquote {{
            border-left: 3px solid var(--accent);
            background: var(--accent-light);
            padding: 1rem 1.25rem;
            margin-bottom: 1.5rem;
            border-radius: 0 8px 8px 0;
            color: var(--text-secondary);
        }}
        .markdown-body details {{
            background: var(--bg-main);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1rem;
        }}
        .markdown-body summary {{
            cursor: pointer; font-weight: 500;
            outline: none; color: var(--text-primary);
        }}

        /* Architecture Layers */
        .arch-layers-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }}
        .arch-layer {{
            background: var(--bg-main);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 1.25rem;
            transition: box-shadow 0.2s;
        }}
        .arch-layer:hover {{ box-shadow: var(--shadow-md); }}
        .arch-layer-name {{
            font-weight: 700;
            font-size: 0.95rem;
            color: var(--accent);
            margin-bottom: 0.4rem;
        }}
        .arch-layer-files {{
            font-size: 0.8rem;
            color: var(--text-muted);
            margin-bottom: 0.6rem;
        }}
        .arch-layer-files code {{
            background: var(--bg-glass);
            border: 1px solid var(--border-glass);
            border-radius: 4px;
            padding: 0.1rem 0.35rem;
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.78rem;
            margin-right: 0.25rem;
        }}
        .arch-layer-desc {{
            font-size: 0.88rem;
            color: var(--text-secondary);
            line-height: 1.5;
        }}

        /* Mermaid diagram container */
        .mermaid-container {{
            background: var(--bg-main);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 2rem;
            margin-bottom: 1.5rem;
            display: flex;
            justify-content: center;
            overflow-x: auto;
        }}

        /* Connections list */
        .connections-visualizer {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            padding: 1rem 0;
        }}
        .showroom-flow-node {{
            background: var(--bg-main);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 0.85rem 1.5rem;
            font-weight: 600;
            font-size: 0.9rem;
            color: var(--text-primary);
            box-shadow: var(--shadow-sm);
        }}
        .showroom-flow-arrow {{
            color: var(--text-muted);
            font-size: 1.2rem;
            padding: 0.15rem 0;
            text-align: center;
        }}
        .flow-relationship {{
            font-size: 0.75rem;
            color: var(--text-muted);
            font-weight: 400;
            display: block;
        }}

        .section-title {{
            font-size: 1.2rem;
            font-weight: 700;
            color: var(--text-primary);
            margin-bottom: 1rem;
        }}

        .footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.8rem;
            padding: 1rem;
        }}
        .footer a {{ color: var(--accent); text-decoration: none; font-weight: 500; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{analysis.get('project_name', 'Project Showroom')}</h1>
            <div class="subtitle">{analysis.get('project_persona', 'Repository Showcase')}</div>
            <div class="tech-badges">
                {tech_badges}
            </div>
        </header>

        <main>
            <div class="tabs-container">
                <div class="tab-bar">
                    <button class="tab-btn active" onclick="switchTab('readme')">Documentation</button>
                    <button class="tab-btn" onclick="switchTab('architecture')">Architecture</button>
                    <button class="tab-btn" onclick="switchTab('quickstart')">Component Flow</button>
                </div>

                <!-- README TAB -->
                <div id="readme-tab" class="tab-content active">
                    <div id="readme-html" class="markdown-body"></div>
                </div>

                <!-- ARCHITECTURE TAB -->
                <div id="architecture-tab" class="tab-content">
                    <div class="section-title">System Architecture Diagram</div>
                    <div class="mermaid-container">
                        <div class="mermaid" id="arch-diagram">{mermaid_graph_str}</div>
                    </div>
                    {f'<div class="section-title" style="margin-top:2rem;">Architecture Layers</div><div class="arch-layers-grid">{arch_layers_html}</div>' if arch_layers_html else ''}
                </div>

                <!-- QUICKSTART TAB -->
                <div id="quickstart-tab" class="tab-content">
                    <div class="section-title">Component Flow</div>
                    <p style="margin-bottom: 1.5rem; color: var(--text-secondary);">How the system connects step-by-step.</p>
                    <div class="connections-visualizer">
                        {self._generate_showroom_flow_html(analysis)}
                    </div>
                </div>
            </div>
        </main>

        <div class="footer">
            Generated by <a href="https://github.com/user/githubReadmeForge" target="_blank">githubReadmeForge</a>
        </div>
    </div>

    <script>
        // Render markdown
        const markdown = `{escaped_readme}`;
        document.getElementById('readme-html').innerHTML = marked.parse(markdown);

        // Initialize Mermaid
        mermaid.initialize({{
            startOnLoad: false,
            theme: 'base',
            themeVariables: {{
                primaryColor: '#e0f2fe',
                primaryTextColor: '#0f172a',
                primaryBorderColor: '#7dd3fc',
                lineColor: '#94a3b8',
                secondaryColor: '#f8fafc',
                tertiaryColor: '#f0f9ff'
            }},
            flowchart: {{ curve: 'basis' }}
        }});

        function switchTab(tabId) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(
                btn => btn.textContent.toLowerCase().includes(tabId === 'readme' ? 'doc' : tabId === 'architecture' ? 'arch' : 'comp')
            );
            if (activeBtn) activeBtn.classList.add('active');

            const activeTab = document.getElementById(tabId + '-tab');
            if (activeTab) activeTab.classList.add('active');

            if (tabId === 'architecture') {{
                const el = document.getElementById('arch-diagram');
                if (el && !el.dataset.rendered && el.textContent.trim() !== 'flowchart TD') {{
                    mermaid.run({{ nodes: [el] }}).then(() => {{
                        el.dataset.rendered = 'true';
                    }}).catch(err => {{
                        console.warn('Mermaid render error:', err);
                        el.innerHTML = '<p style="color:#94a3b8;font-size:0.85rem;">Architecture diagram unavailable for this project.</p>';
                    }});
                }}
            }}
        }}

        // Also render any mermaid blocks inside the README markdown
        document.addEventListener('DOMContentLoaded', function() {{
            document.querySelectorAll('.markdown-body pre code.language-mermaid').forEach(block => {{
                const container = document.createElement('div');
                container.className = 'mermaid';
                container.textContent = block.textContent;
                block.parentElement.replaceWith(container);
            }});
            mermaid.run({{ querySelector: '.markdown-body .mermaid' }}).catch(() => {{}});
        }});
    </script>
</body>
</html>
"""
        return html_content

    def _generate_showroom_flow_html(self, analysis):
        """Converts connections to visual stack blocks for the Component Flow tab."""
        connections = analysis.get("connections", [])
        if not connections:
            return "<div style='color:var(--text-muted);font-size:0.9rem;'>No component connections mapped for this project.</div>"

        nodes = []
        seen = set()
        for c in connections:
            c_dict = self._safe_get_dict(c)
            src = c_dict.get("from", "")
            dst = c_dict.get("to", "")
            if src and src not in seen:
                nodes.append({"name": src, "rel": c_dict.get("relationship", "")})
                seen.add(src)
            if dst and dst not in seen:
                nodes.append({"name": dst, "rel": ""})
                seen.add(dst)

        html = []
        for idx, node in enumerate(nodes):
            rel_html = ""
            if idx < len(nodes) - 1 and idx < len(connections):
                c_dict = self._safe_get_dict(connections[idx])
                if c_dict.get("relationship"):
                    rel_label = c_dict.get("relationship", "")
                    rel_html = f'<span class="flow-relationship">{rel_label}</span>'

            html.append(f'<div class="showroom-flow-node">{node["name"]}</div>')
            if idx < len(nodes) - 1:
                html.append(f'<div class="showroom-flow-arrow">↓ {rel_html}</div>')

        return "\n".join(html)
