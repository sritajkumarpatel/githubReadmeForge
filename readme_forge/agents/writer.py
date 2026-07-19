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

        # Map legacy style names to the new 5-style system for backward compatibility.
        legacy_style_map = {
            "minimalist": "minimal",
            "enterprise": "reference",
            "visual_rich": "narrative",
        }
        resolved_style = legacy_style_map.get(style, style)

        style_instruction = self._get_style_instruction(resolved_style)

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
        include_header_banner = True
        if style == "visual_rich" and output_dir:
            visual_generator = VisualAssetGenerator(Path(output_dir))

            # Determine visual pack: brief overrides > classification suggestion > intent map > fallback
            if brief:
                visual_pack = brief.get("visual_pack", "ui_app")
                no_external_assets = bool(brief.get("no_external_assets"))
                include_header_banner = bool(brief.get("include_header_banner", True))
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
                "   Immediately below the H1 title, add a row of standard, professional shields.io badges. "
                "You must include the following badges:\n"
                "   - **Build Status / CI/CD**: A GitHub Actions status badge (use github/actions/workflow/status/{owner}/{repo}/{workflow_file}.yml if workflows exist, or fallback to a template status badge).\n"
                "   - **Language / Version**: A badge showing the primary language and version (e.g., Python 3.10+, Node.js >=18, etc. matching the codebase language).\n"
                "   - **License**: A badge showing the project's license (e.g., MIT, Apache 2.0, or whatever license is detected/analyzed).\n"
                "   - **Testing / Coverage**: A code coverage or test pass status badge (if the project has tests).\n"
                "   Format all badges as standard markdown badge links using shields.io style flat-square or flat for a premium look."
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
                "      - Generate a native Mermaid.js flowchart TD diagram inside a markdown code block showing the connections and data flows. Use ONLY alphanumeric node IDs and quoted labels like A[\"Label\"] to prevent syntax errors.\n"
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
                "14. **Contributing & License**: Clean links to CONTRIBUTING.md, LICENSE, and testing run instructions.\n"
                "    - SPECIAL GRATITUDE PRESERVATION RULE: If the existing README has any thanks, acknowledgements, gratitude, or 'Thank You' sections at the bottom, you MUST preserve them and append them at the end of this section to keep the project's original sentiment."
            ),
        }

        layout_sections = []
        for sec in planned_sections:
            if sec in layout_dict:
                layout_sections.append(layout_dict[sec])
            elif sec == "testing" and "contributing_license" not in planned_sections:
                layout_sections.append("**. **Testing**: Document test instructions and command lines to run the test suite.")

        layout_text = "\n\n".join(layout_sections)

        style_guardrails = self._get_style_guardrails(resolved_style)

        system_prompt = (
            "You are an expert technical writer and product storyteller.\n"
            "Your task is to write a HIGHLY POLISHED, PROFESSIONAL README.md for a project codebase.\n\n"
            "CRITICAL PHILOSOPHY:\n"
            "- Every section must have DEPTH and SPECIFICITY. No generic filler text.\n"
            "- Extract REAL details from the codebase — real file names, real commands, real config variables.\n"
            "- Be SPECIFIC over generic. 'Pydantic-based, OpenAPI-compatible' beats 'easy to use'.\n\n"
            "FACTUALITY RULES:\n"
            "- Treat the supplied documentation plan and facts as authoritative.\n"
            "- Do not invent commands, flags, endpoints, environment variables, badges, versions, owners, or test results.\n"
            "- Omit any section that is not in the documentation plan.\n"
            "- If facts are incomplete, write a concise evidence-only README rather than plausible filler.\n\n"
            f"Project Type Context:\n{project_type_instruction}\n\n"
            f"README Style (modeled after top-rated GitHub projects):\n{style_instruction}\n\n"
            f"Style-Specific Hard Rules:\n{style_guardrails}\n\n"
            f"Language settings:\n{lang_instruction}\n\n"
            "ANTI-PATTERNS TO AVOID (these appear in generated READMEs but never in top open-source projects):\n"
            "- Generic 'Problem' sections that could apply to any software.\n"
            "- ASCII art or placeholder diagrams instead of real Mermaid or sourced images.\n"
            "- 'Repository Structure' sections that just list files without explaining them.\n"
            "- Fluffy 'automates X' or 'delivers Y' filler phrases without specific technical claims.\n"
            "- Missing screenshots/GIFs for any UI/visual project.\n"
            "- Bare URLs without descriptions.\n\n"
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
            "- For the architecture section, you MUST generate a native Mermaid.js flowchart TD diagram inside a markdown code block showing the connections and data flows. Use ONLY quoted labels like A[\"Label\"] to prevent syntax errors.\n"
            "- Keep all facts strict and derived from codebase scan results; do not invent files, endpoints, or features.\n"
            "- Preserving gratitude: If the existing README (provided in the user prompt) has any acknowledgements, thanks, or 'Thank You' sections at the bottom, carry them forward to the end of the contributing_license section.\n"
            "- If a 'Check Out the Demo' section is supplied in the user prompt (when the project is visual but has no real assets), include it VERBATIM. Do not paraphrase or reformat it — it is a curated placeholder for the project owner to fill in later."
        )

        # Differentiation and visual asset context
        differentiators = analysis.get("differentiators") or []
        differentiators_text = "\n".join(f"- {d}" for d in differentiators) if differentiators else ""
        ui_assets = analysis.get("ui_assets") or []
        ui_assets_text = "\n".join(f"- {a}" for a in ui_assets) if ui_assets else ""

        # installation_methods
        install_methods = analysis.get("installation_methods") or []
        install_methods_text = ""
        for m in install_methods:
            if not isinstance(m, dict):
                continue
            name = m.get("name", "")
            command = m.get("command", "")
            desc = m.get("description", "")
            if command:
                install_methods_text += f"- **{name}**: `{command}` ({desc})\n"

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

        if differentiators_text:
            user_prompt += (
                "Concrete differentiators (use these for the Solution section):\n"
                f"{differentiators_text}\n\n"
            )

        if ui_assets_text:
            user_prompt += (
                "Visual assets available in the repo (use these paths for hero/demo if appropriate):\n"
                f"{ui_assets_text}\n\n"
            )

        if install_methods_text:
            user_prompt += (
                "Detected installation methods (use these in the Installation section):\n"
                f"{install_methods_text}\n\n"
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

        # Demo placeholder: tell the LLM to include a "Check Out the Demo" section
        # when the project is visual but has no real assets to embed.
        demo_placeholder_text = ""
        if self._should_include_demo_placeholder(analysis):
            demo_placeholder_text = self._get_demo_placeholder_section()
            user_prompt += (
                "\nVISUAL PROJECT — NO REAL ASSETS DETECTED:\n"
                "The project appears to have a visual interface but no real images, GIFs, or "
                "videos are available in the repository. Include a 'Check Out the Demo' section "
                "in the README using the exact text below verbatim. This reserves the spot for "
                "the project owner to drop in real visuals later.\n\n"
                "=== DEMO SECTION TO INSERT ===\n"
                f"{demo_placeholder_text}\n"
                "=== END DEMO SECTION ===\n"
            )

        readme_markdown = self.llm_client.generate(system_prompt, user_prompt)

        # Keep Mermaid blocks natively as requested by user. We no longer replace them with SVGs.

        if include_header_banner and visual_intro and "assets/readme/brand-light.svg" not in readme_markdown:
            readme_markdown = f"{visual_intro}\n\n{readme_markdown.lstrip()}"

        # If the LLM didn't include the demo section verbatim (some models paraphrase),
        # append it ourselves so the placeholder is always present.
        if demo_placeholder_text and "Check Out the Demo" not in readme_markdown:
            readme_markdown = readme_markdown.rstrip() + "\n\n" + demo_placeholder_text

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

    def _get_style_instruction(self, style: str) -> str:
        """Return the system-prompt instruction block for a given README style.

        Each style was modeled after a category of real top-rated GitHub projects:
          - reference: Axios, ripgrep, FastAPI, gh CLI (libraries, CLIs, APIs)
          - narrative: Supabase, AppFlowy, Plausible, Moby (products, frameworks)
          - tutorial: build-your-own-x, freeCodeCamp (learning resources)
          - showcase: AppFlowy, Phaser, httpie (UI products with visual demos)
          - minimal: jq, Three.js, tldr (small utilities)
        """
        instructions = {
            "reference": (
                "STYLE: REFERENCE (USER MANUAL)\n"
                "You are writing a USER MANUAL, not a marketing page. The reader is technical. Trust them.\n"
                "REQUIREMENTS:\n"
                "- Lead with a one-line tagline and 3-5 shields.io badges (license, version, build, downloads).\n"
                "- The FIRST code block must be a working install command. Do not bury it.\n"
                "- Quick Start must show 5-15 lines of runnable code WITH expected output.\n"
                "- Include an exhaustive API/Command Reference section — every public symbol, not a curated subset.\n"
                "- Use tables for configuration options (env vars, flags, settings).\n"
                "- Each Feature bullet must include WHY it matters, not just WHAT it is.\n"
                "- OMIT 'The Problem' and 'The Solution' sections. The reader knows what a CLI tool is.\n"
                "- Use <details> blocks for optional deep dives.\n"
                "ANTI-PATTERNS: 'easy to use', 'simple', 'powerful', 'flexible' without a concrete example. Marketing prose. Long preambles."
            ),
            "narrative": (
                "STYLE: NARRATIVE (STORY)\n"
                "You are telling a STORY. Sell the project to a developer who is considering whether to use it.\n"
                "REQUIREMENTS:\n"
                "- Lead with: Logo → Tagline → 3-4 badges → 1-line mission.\n"
                "- 'The Problem': 2-3 sentences with a CONCRETE pain point. Not 'documentation is hard' but the specific frustration this tool eliminates.\n"
                "- 'The Solution': 3-5 sentences with CONCRETE differentiators. Use the `differentiators` field from analysis if available. Examples: 'Single static binary', 'Zero dependencies', 'OpenAPI-compatible'.\n"
                "- 'How It Works': A Mermaid flowchart TD diagram using only nodes from the actual `connections` data. Quote labels: A[\"Label\"]. If <3 connections, SKIP the diagram and use a feature grid instead.\n"
                "- Features: 6-10 bullets, EACH with a concrete example or a link to docs.\n"
                "- Quick Start: 3-5 lines of working code.\n"
                "- OMIT 'The Problem' if `problem_statement` is empty or generic — start with 'About' instead.\n"
                "ANTI-PATTERNS: Generic Problem sections. ASCII art placeholders. Fluffy 'automates X' filler. Repository Structure that just lists files without explaining them."
            ),
            "tutorial": (
                "STYLE: TUTORIAL (LEARNING PATH)\n"
                "You are TEACHING. The reader is a learner. Make the path explicit.\n"
                "REQUIREMENTS:\n"
                "- Lead with a mission statement and 1-2 hero images if available (use `ui_assets`).\n"
                "- 'What You'll Learn': 3-5 specific outcomes, each one concrete (e.g., 'Build a REST API with FastAPI', not 'Learn FastAPI').\n"
                "- 'Prerequisites': what the reader needs before starting (tools, prior knowledge).\n"
                "- Table of Contents: a categorized list of resources or sub-tutorials, each with a 1-sentence description.\n"
                "- 'Getting Started': first 5-minute exercise with copy-pasteable commands.\n"
                "- 'Resources': external links to docs, books, courses — each with a description.\n"
                "OMIT: Installation (tutorial repos are not installed), API Reference, Configuration.\n"
                "ANTI-PATTERNS: Long preambles. Generic 'this will teach you X' claims. Bare URLs without descriptions."
            ),
            "showcase": (
                "STYLE: SHOWCASE (VISUAL PRODUCT PAGE)\n"
                "You are presenting a PRODUCT. Show, don't tell. Visuals are mandatory.\n"
                "REQUIREMENTS:\n"
                "- Lead with: Logo → Tagline → 1-2 HERO IMAGES (use paths from `ui_assets` if available; otherwise describe the visual).\n"
                "- 'Try It Now': 1-3 commands that get the user running in <5 minutes.\n"
                "- Features: 6-10 items, each referencing a visual or screenshot path. If no image is available, describe the screen concretely.\n"
                "- 'Use Cases': 2-3 mini-stories of who uses this and why. Concrete, not abstract.\n"
                "- 'Built With': a one-line tech stack summary (use `tech_stack`).\n"
                "- 'Community': Discord/forum link if known.\n"
                "OMIT: Long problem/solution narratives, exhaustive API references.\n"
                "ANTI-PATTERNS: Walls of text without visuals. Generic feature lists. Missing hero image references."
            ),
            "minimal": (
                "STYLE: MINIMAL (TRAILER)\n"
                "You are a TRAILER. The README points to real docs elsewhere. Be brief.\n"
                "REQUIREMENTS:\n"
                "- Maximum length: 60 lines. If you exceed it, cut.\n"
                "- Lead with: Title → Tagline → Install command → Usage example.\n"
                "- 3-5 lines for the usage example.\n"
                "- If the project has external docs, defer to them with a single link.\n"
                "- OMIT: Features, Architecture, Configuration, Problem/Solution, Use Cases.\n"
                "ANTI-PATTERNS: Long preambles. Marketing prose. Multi-section layouts."
            ),
        }
        return instructions.get(style, instructions["narrative"])

    def _get_style_guardrails(self, style: str) -> str:
        """Return hard rules the LLM must follow for a given style."""
        guardrails = {
            "reference": (
                "HARD RULES:\n"
                "- The first code block in the README must be a working install command.\n"
                "- The Quick Start section MUST include expected output, not just code.\n"
                "- Never use 'easy to use', 'simple', 'powerful', or 'flexible' without a concrete example.\n"
                "- The API/Command Reference section must enumerate every public symbol/flag, not a curated subset."
            ),
            "narrative": (
                "HARD RULES:\n"
                "- If `problem_statement` is empty or generic, OMIT 'The Problem' section and start with 'About'.\n"
                "- The 'How It Works' diagram must use ONLY nodes from the actual connections/architecture data. Quote all labels.\n"
                "- Every feature bullet must include either: a code snippet, a link to docs, or a specific outcome.\n"
                "- Every 'Solution' claim must reference a concrete technical choice from `differentiators`."
            ),
            "tutorial": (
                "HARD RULES:\n"
                "- Never include an Installation section. Tutorial repos don't get installed.\n"
                "- The Table of Contents must be the centerpiece, organized by category.\n"
                "- Every link must have a 1-sentence description (avoid bare URLs).\n"
                "- 'What You'll Learn' must list concrete outcomes, not abstract goals."
            ),
            "showcase": (
                "HARD RULES:\n"
                "- The first image after the title must be a hero screenshot/GIF path (from `ui_assets`) or a 'see it in action' description.\n"
                "- The 'Try It Now' section must run in <5 minutes on a fresh machine.\n"
                "- Each feature must have a visual reference (image path or concrete description).\n"
                "- 'Use Cases' must include 2-3 concrete user stories."
            ),
            "minimal": (
                "HARD RULES:\n"
                "- Hard cap: 60 lines.\n"
                "- Never include a Features section.\n"
                "- Never include an Architecture section.\n"
                "- If the project has external docs, defer to them with a single link."
            ),
        }
        return guardrails.get(style, guardrails["narrative"])

    def _should_include_demo_placeholder(self, analysis: dict) -> bool:
        """Decide whether the README should include a 'Check Out the Demo' placeholder.

        Returns True only when:
          - The project is a visual project (has_visual_interface OR style is showcase/narrative)
          - AND there are NO real image/video assets in the repo
        """
        if not analysis:
            return False
        has_visual = bool(analysis.get("has_visual_interface"))
        recommended = analysis.get("recommended_style", "")
        style_visual = recommended in {"showcase", "narrative", "demo"}
        if not (has_visual or style_visual):
            return False
        # If the project already has real assets, do not add a placeholder.
        hero_assets = analysis.get("hero_assets") or []
        ui_assets = analysis.get("ui_assets") or []
        if hero_assets or ui_assets:
            return False
        return True

    def _get_demo_placeholder_section(self) -> str:
        """Return a friendly 'Check Out the Demo' placeholder section.

        This section reserves a spot in the README for the project owner to drop
        in a screenshot, GIF, or video link. It is honest about the gap, gives
        clear instructions, and is visually distinctive so a maintainer notices it.
        """
        return (
            "## 🎬 Check Out the Demo\n\n"
            "> 📸 **A live demo is coming soon!**\n>\n"
            "> This space will soon be filled with screenshots, GIFs, or a video walkthrough.\n"
            "> Thank you for waiting while we put the finishing touches on it.\n>\n"
            "> **Want to help?** Drop a screenshot, a quick GIF, or a link to a Loom/YouTube "
            "video right under this callout, and open a PR — the maintainers (and visitors) "
            "will thank you for it.\n\n"
            "**How to contribute the demo:**\n"
            "\n"
            "1. Capture a short screen recording or take a few screenshots of the project in action.\n"
            "2. Save the file under `assets/` or `docs/` in the repository (e.g. `assets/demo.gif`).\n"
            "3. Replace the callout above with one of the following:\n"
            "    - Image: `![Demo screenshot](assets/demo.png)`\n"
            "    - GIF: `![Demo](assets/demo.gif)`\n"
            "    - Video: `[▶ Watch the demo](https://your-video-link-here)`\n"
            "4. Open a pull request.\n"
        )
