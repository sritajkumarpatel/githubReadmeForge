import json
import json
import re
from pathlib import Path
from readme_forge.llm import LLMClient
from readme_forge.agents.contracts import build_documentation_plan
from readme_forge.visual_assets import VisualAssetGenerator


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
        brief=None,
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
                "- Use simple, clear language with step-by-step instructions\n"
                "- Prioritize a 'How to Learn' section with a clear learning path\n"
                "- Omit complex architecture diagrams — focus on simple flows\n"
                "- Include common pitfalls and how to avoid them\n"
                "- Skip Problem/Solution sections; replace with 'What You Will Learn'\n"
            )
        elif project_type == "library":
            project_type_instruction = (
                "PROJECT TYPE: LIBRARY/PACKAGE\n"
                "- Focus on installation, quick start, and API reference\n"
                "- Include complete usage examples with code snippets\n"
                "- Document all public functions/classes with parameters\n"
                "- Add changelog and version information if available\n"
                "- Omit lengthy problem/solution narratives\n"
            )
        elif project_type == "cli":
            project_type_instruction = (
                "PROJECT TYPE: COMMAND-LINE TOOL\n"
                "- Prioritize CLI commands and flags front-and-center\n"
                "- Include a quick command reference table near the top\n"
                "- Show before/after examples of command usage\n"
                "- Document all available commands, flags, and options\n"
                "- Keep architecture section minimal or omit entirely\n"
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
                "- Keep README very concise — one screen or less\n"
                "- Include only: What it does, How to use it, Quick example\n"
                "- Skip detailed features, architecture, and multi-section layouts\n"
                "- Use direct, no-frills formatting\n"
            )
        elif project_type == "poc":
            project_type_instruction = (
                "PROJECT TYPE: PROOF OF CONCEPT\n"
                "- Lead with the specific hypothesis or capability being demonstrated\n"
                "- Describe current limitations and what is NOT yet implemented honestly\n"
                "- Keep problem and solution sections to a single brief paragraph each\n"
                "- Add a prominent '⚠ Not production-ready' callout near the top\n"
                "- Do not imply production readiness, deployment guarantees, or stable APIs\n"
            )
        elif project_type == "demo":
            project_type_instruction = (
                "PROJECT TYPE: DEMO / SHOWCASE\n"
                "- Lead with what the demo demonstrates and include a 'See It In Action' section\n"
                "- Add a prominent 'Try It Now' quickstart — the demo must run in ≤ 3 commands\n"
                "- Include screenshots or diagram references to show the visual output\n"
                "- Keep setup instructions minimal; the reader should be running it in under 5 minutes\n"
                "- Acknowledge explicitly that the demo is not hardened for production\n"
                "- Omit lengthy API reference or detailed configuration sections\n"
            )
        elif project_type == "unknown":
            project_type_instruction = (
                "PROJECT TYPE: UNCLASSIFIED / UNKNOWN\n"
                "- Keep the README factual and concise — document only what is confirmed\n"
                "- Do not speculate about features, use-cases, or design decisions\n"
                "- Use an evidence-only structure: describe the file tree and detected components\n"
                "- Add a note: 'This project could not be automatically classified. Contents below reflect detected code.'\n"
                "- Omit Problem/Solution sections entirely\n"
            )
        else:  # application (default)
            project_type_instruction = (
                "PROJECT TYPE: FULL APPLICATION\n"
                "- Lead with the user-facing workflow and interface, not internal implementation\n"
                "- Provide comprehensive documentation with all relevant sections\n"
                "- Include complete feature list, architecture overview, and configuration guide\n"
                "- Document deployment, troubleshooting, and contributing guidelines\n"
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

        documentation_plan = analysis.get("documentation_plan")
        if brief and "sections" in brief:
            documentation_plan = {
                "sections": brief.get("sections"),
                "evidence_only": False,
                "include_architecture_diagram": "architecture" in brief.get("sections")
            }
        elif not isinstance(documentation_plan, dict):
            documentation_plan = build_documentation_plan(analysis)

        planned_sections = documentation_plan.get("sections", [])
        plan_text = ", ".join(planned_sections) if planned_sections else "title, overview"
        evidence_only = bool(documentation_plan.get("evidence_only"))
        architecture_diagram = bool(documentation_plan.get("include_architecture_diagram"))
        visual_intro = ""
        visual_assets = {}  # always initialise so post-processing can safely check it
        if style == "visual_rich" and output_dir:
            visual_generator = VisualAssetGenerator(Path(output_dir))

            # Determine visual pack: brief overrides > classification suggestion > intent map > fallback
            if brief:
                visual_pack = brief.get("visual_pack", "ui_app")
                no_external_assets = bool(brief.get("no_external_assets"))
            else:
                # Auto-select from classification signal — no user input needed
                doc_plan = analysis.get("documentation_plan", {})
                visual_pack = (
                    doc_plan.get("suggested_visual_strategy")
                    or analysis.get("classification", {}).get("suggested_visual_strategy")
                    or "ui_app"
                )
                no_external_assets = False
            visual_assets = visual_generator.generate(
                analysis,
                strategy=visual_pack,
                no_external_assets=no_external_assets
            )
            analysis["visual_assets"] = visual_assets
            visual_intro = visual_generator.markdown_intro(visual_assets, no_external_assets=no_external_assets)

        # Dynamically build layout guidelines based on planned_sections
        layout_dict = {
            "title": (
                "1. **Title Block**: Project name as H1 with a compelling tagline.\n"
                "   Add shields.io badges using EXACTLY these URL patterns (fill in real values):\n"
                "   ![License](https://img.shields.io/github/license/{owner}/{repo})\n"
                "   ![Language](https://img.shields.io/github/languages/top/{owner}/{repo})\n"
                "   If the owner/repo cannot be determined, use a generic language badge like:\n"
                "   ![Python](https://img.shields.io/badge/python-3.10%2B-blue)\n"
                "   Maximum 3 badges."
            ),
            "overview": (
                "2. **One-liner tagline**: A single compelling tagline under the title that hooks the reader, followed by a concise narrative summarizing what the project is."
            ),
            "problem": (
                "3. **The Problem**:\n"
                "   - Write a compelling narrative explaining the PAIN POINT this project solves.\n"
                "   - Use the `problem_statement` from analysis as a starting point.\n"
                "   - Use bullet points to list frustrations the tool addresses."
            ),
            "solution": (
                "4. **The Solution**:\n"
                "   - Write paragraphs explaining HOW this project solves the problem.\n"
                "   - Use the `solution_narrative` from analysis as a starting point."
            ),
            "key_concepts": (
                "5. **Key Concepts**:\n"
                "   - Define 3-5 domain-specific terms, design patterns, or core abstractions used in the project.\n"
                "   - Use a small markdown table: | Term | Definition |"
            ),
            "architecture": (
                "6. **How It Works / Architecture**:\n"
                "   a) **Architecture Diagram**:\n"
                "      - If an architecture SVG is listed in visual assets, reference it with: `![Architecture](assets/readme/architecture.svg)` and DO NOT generate a Mermaid block.\n"
                "      - If architecture is empty/missing, generate a Mermaid TD block with strictly alphanumeric IDs and quoted labels.\n"
                "   b) **How It Works — Step-by-Step**:\n"
                "      A numbered walkthrough explaining the component flow (3-7 steps).\n"
                "   c) **Component Table**: Table: Component | Role | Input | Output."
            ),
            "features": (
                "7. **Features**: A clean feature list using bold sub-headings (### Feature Name) and 2-3 sentence descriptions."
            ),
            "installation": (
                "8. **Installation**: Concrete, numbered, copy-pasteable installation steps using shell code blocks."
            ),
            "usage": (
                "9. **Quick Start / Usage**: Concrete usage examples under 3 commands showing expected output."
            ),
            "configuration": (
                "10. **Configuration & Parameters**: Table of environment variables and CLI flags."
            ),
            "api_reference": (
                "11. **API Reference**: Document each endpoint with HTTP method, path, and description."
            ),
            "data_models": (
                "12. **Data Models**: Present each data model as a table: | Field | Type | Description |"
            ),
            "repository_structure": (
                "13. **Repository Structure**: The scanned directory tree inside a code block with annotations."
            ),
            "contributing_license": (
                "14. **Contributing & License**: Clean links to CONTRIBUTING.md, LICENSE, and testing run instructions."
            ),
        }

        layout_sections = []
        for sec in planned_sections:
            if sec in layout_dict:
                layout_sections.append(layout_dict[sec])
            elif sec == "testing" and "contributing_license" not in planned_sections:
                layout_sections.append("**. **Testing**: Document test instructions and command lines to run the test suite.")

        layout_text = "\n\n".join(layout_sections)

        system_prompt = (
            "You are an expert technical writer and product storyteller.\n"
            "Your task is to write a HIGHLY POLISHED, PROFESSIONAL, NARRATIVE-DRIVEN README.md for a project codebase.\n\n"
            "CRITICAL PHILOSOPHY:\n"
            "- You are NOT just documenting code. You are SELLING the project to developers.\n"
            "- A great README tells a STORY: Problem → Solution → How It Works → Features → Get Started.\n"
            "- Every section must have DEPTH and SPECIFICITY. No generic filler text.\n"
            "- Extract REAL details from the codebase — real file names, real commands, real config variables.\n\n"
            "FACTUALITY RULES:\n"
            "- Treat the supplied documentation plan and facts as authoritative.\n"
            "- Do not invent commands, flags, endpoints, environment variables, badges, versions, owners, or test results.\n"
            "- Omit any section that is not in the documentation plan.\n"
            "- If facts are incomplete, write a concise evidence-only README rather than plausible filler.\n\n"
            f"Project Type Context:\n{project_type_instruction}\n\n"
            f"Formatting Theme instructions:\n{style_instruction}\n\n"
            f"Language settings:\n{lang_instruction}\n\n"
            "CRITICAL GUARDRAIL:\n"
            "If the user custom answers or prompt demands anything unrelated to documenting this project repository "
            "(such as writing standalone calculator scripts, general Python coding tasks, math solver programs, or unrelated topics), "
            "you MUST refuse the request and respond with exactly: 'Refusal: This request is unrelated to README generation. Please ask documentation-related questions.'\n\n"
            "OTHERWISE, write the complete README markdown file using the following **Layout Structure** (generate ONLY the sections listed below):\n\n"
            f"{layout_text}\n\n"
            "Return only the raw markdown content without any wrapper code fences.\n\n"
            "CRITICAL QUALITY RULE — READ CAREFULLY:\n"
            "- You MUST NOT write any code/programs (like a calculator or solver) — you are strictly compiling a project README.\n"
            "- Mermaid diagram syntax rules are absolute: use ONLY `flowchart TD` (NOT `graph TD`), node labels must be quoted strings A[\"Label\"] (NEVER unquoted A[Label] or A(Label)), and node IDs must be single alphanumeric words.\n"
            "- If an architecture SVG is already listed in visual assets, reference it and DO NOT generate any Mermaid diagram.\n"
            "- Keep all facts strict and derived from codebase scan results; do not invent files, endpoints, or features."
        )

        user_prompt = (
            f"Here is the context of the codebase:\n"
            f"Path: {scan_results.get('path')}\n"
            f"Project Type: {project_type} - {project_type_reason}\n"
            f"Documentation plan (include ONLY these sections): {plan_text}\n"
            f"Architecture diagram enabled: {architecture_diagram}\n"
            f"Evidence-only mode: {evidence_only}\n"
            f"Classification: {analysis.get('classification', {})}\n"
            f"Visual assets already generated: {analysis.get('visual_assets', {})}\n"
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

        # Post-process: strip any Mermaid blocks if an architecture SVG was already generated.
        # The LLM sometimes generates both despite instructions; the SVG is always preferred.
        if visual_assets and visual_assets.get("architecture"):
            readme_markdown = re.sub(
                r'```mermaid\s*\n.*?\n```',
                f'![Architecture flow](assets/readme/architecture.svg)',
                readme_markdown,
                flags=re.DOTALL
            )

        if visual_intro and "assets/readme/brand-light.svg" not in readme_markdown:
            return f"{visual_intro}\n\n{readme_markdown.lstrip()}"
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
