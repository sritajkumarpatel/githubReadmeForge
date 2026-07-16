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

    def generate_readme(self, scan_results, analysis, interactive_answers=None, style="visual_rich", output_dir=None, target_path_or_url=None, lang="en"):
        """Generates the content of a polished, narrative-driven, professional README.md using deep codebase context and analysis."""
        
        # 1. Hero banner generation removed - using clean title block instead

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
            # Build switcher label
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
        else:  # application
            project_type_instruction = (
                "PROJECT TYPE: FULL APPLICATION\n"
                "- Comprehensive documentation with all sections\n"
                "- Include complete feature list and architecture\n"
                "- Document configuration, deployment, and troubleshooting\n"
                "- Add contributing guidelines and license\n"
            )

        # Build rich context from analysis data
        features_context = ""
        for feat in analysis.get("key_features", []):
            features_context += f"- {feat.get('name', '')}: {feat.get('description', '')} (Category: {feat.get('category', 'General')})\n"
        
        api_context = ""
        for ep in analysis.get("api_endpoints", []):
            api_context += f"- {ep.get('method', 'GET')} {ep.get('path', '')}: {ep.get('description', '')}\n"
        
        config_context = ""
        for cv in analysis.get("config_variables", []):
            req = "Required" if cv.get("required") else "Optional"
            config_context += f"- {cv.get('name', '')}: {cv.get('description', '')} ({req}, default: {cv.get('default', 'N/A')})\n"
        
        cli_context = ""
        for cmd in analysis.get("cli_commands", []):
            cli_context += f"- `{cmd.get('command', '')}`: {cmd.get('description', '')}\n"

        system_prompt = (
            "You are an expert technical writer and product storyteller.\n"
            "Your task is to write a HIGHLY POLISHED, PROFESSIONAL, NARRATIVE-DRIVEN README.md for a project codebase.\n\n"
            "CRITICAL PHILOSOPHY:\n"
            "- You are NOT just documenting code. You are SELLING the product to developers.\n"
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
            "1. **Title Block**: Project name as H1 with a compelling tagline. Add shields.io badges for: license, language count, and CI/CD status if applicable.\n\n"
            "4. **The Problem** (MANDATORY): Write a compelling 2-3 paragraph narrative explaining the PAIN POINT this project solves.\n"
            "   - Use the `problem_statement` from analysis as a starting point, but EXPAND it into a relatable story.\n"
            "   - Write from the developer's perspective: 'Every developer has been there...'\n"
            "   - Use bullet points to list specific frustrations the tool addresses.\n"
            "   - This section must make the reader FEEL the pain before showing the solution.\n\n"
            "5. **The Solution** (MANDATORY): Write 2-3 paragraphs explaining HOW this project solves the problem.\n"
            "   - Use the `solution_narrative` from analysis as a starting point, but EXPAND it.\n"
            "   - Explain the key approach (e.g., 'It uses three AI agents to...', 'It provides a single CLI command to...')\n"
            "   - Highlight what makes it different from alternatives.\n\n"
            "6. **How It Works**: Include BOTH:\n"
            "   a) A Mermaid.js diagram showing the actual component flow (use real file names from the codebase)\n"
            "   b) A markdown table showing each major component, its role, input, and output\n"
            "   c) An ASCII or box-diagram showing the data pipeline (Input → Processing → Output)\n\n"
            "7. **Features**: Create a clean feature list with:\n"
            "   - A bold feature name as a sub-heading\n"
            "   - A 2-3 sentence description explaining what it does and why it matters\n"
            "   - Group related features logically\n"
            "   - Use simple dash (-) markers, no emojis\n\n"
            "8. **Quick Start / Usage**: Concrete, copy-pasteable installation and usage examples:\n"
            "   - Installation steps (git clone, pip install, npm install, etc.)\n"
            "   - Basic usage command with expected output\n"
            "   - Advanced usage examples if applicable\n"
            "   - Use the `cli_commands` from analysis data if available\n\n"
            "9. **Configuration & Parameters**: Comprehensive setup docs:\n"
            "   - Environment variables table (Variable | Description | Required | Default)\n"
            "   - CLI flags table if applicable (Flag | Short | Description | Default)\n"
            "   - Use the `config_variables` and `cli_commands` from analysis data\n"
            "   - Use collapsible `<details>` blocks for verbose tables\n\n"
            "10. **API Reference** (only if api_endpoints exist): Document each endpoint with:\n"
            "    - HTTP method and path\n"
            "    - Request body JSON example\n"
            "    - Response JSON example\n"
            "    - Use the `api_endpoints` from analysis data\n\n"
            "11. **Repository Structure**: The scanned directory tree with brief annotations for key directories.\n\n"
            "12. **Contributing & License**: Clean links to CONTRIBUTING.md and LICENSE if they exist.\n\n"
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
        
        if features_context:
            user_prompt += f"Key Features extracted:\n{features_context}\n"
        if api_context:
            user_prompt += f"API Endpoints detected:\n{api_context}\n"
        if config_context:
            user_prompt += f"Configuration Variables found:\n{config_context}\n"
        if cli_context:
            user_prompt += f"CLI Commands available:\n{cli_context}\n"

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
            from_node = c.get('from', 'Unknown')
            to_node = c.get('to', 'Unknown')
            relationship = c.get('relationship', '')
            lines.append(f"- {from_node} → {to_node}: {relationship}")
        return "\n".join(lines)

    def generate_showroom_html(self, readme_markdown, analysis):
        """Generates a premium glassmorphic Showroom HTML file that renders the README dynamically and includes rich visual tabs/animations."""
        
        # We can construct a highly interactive static HTML template.
        # It imports Mermaid.js and marked.js (markdown parser) via CDN so it loads dynamically,
        # and styles it with a sleek, glowing dark glassmorphism CSS interface, tabs, and copy-buttons.

        import json
        escaped_readme = json.dumps(readme_markdown)[1:-1]

        tech_badges = ""
        for tech in analysis.get("tech_stack", [])[:6]:
            tech_badges += f'<span class="tech-badge">{tech}</span> '

        # Build Mermaid connections graph safely with real newlines
        mermaid_connections = ["graph TD"]
        for c in analysis.get('connections', []):
            from_node = c.get('from', '').replace(' ', '_').replace('-', '_')
            to_node = c.get('to', '').replace(' ', '_').replace('-', '_')
            label_from = c.get('from', '')
            label_to = c.get('to', '')
            mermaid_connections.append(f'    {from_node}["{label_from}"] --> {to_node}["{label_to}"]')
        
        mermaid_graph_str = "\n".join(mermaid_connections)

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

        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
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
            font-weight: 700;
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

        main {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }}

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
        }}

        .tab-btn:hover {{
            color: var(--text-secondary);
        }}

        .tab-btn.active {{
            color: var(--accent);
        }}

        .tab-btn.active::after {{
            content: '';
            position: absolute;
            bottom: -1px;
            left: 0;
            width: 100%;
            height: 2px;
            background: var(--accent);
        }}

        .tab-content {{
            padding: 2.5rem;
            display: none;
        }}

        .tab-content.active {{
            display: block;
        }}

        /* Markdown styling inside showroom */
        .markdown-body {{
            line-height: 1.7;
            color: var(--text-primary);
        }}

        .markdown-body h2 {{
            font-size: 1.5rem;
            font-weight: 600;
            margin-top: 2rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--border-glass);
            padding-bottom: 0.5rem;
            color: var(--text-primary);
        }}

        .markdown-body h3 {{
            font-size: 1.2rem;
            font-weight: 600;
            margin-top: 1.5rem;
            margin-bottom: 0.75rem;
            color: var(--text-primary);
        }}

        .markdown-body p {{
            margin-bottom: 1rem;
            color: var(--text-secondary);
        }}

        .markdown-body ul, .markdown-body ol {{
            margin-left: 1.5rem;
            margin-bottom: 1rem;
            color: var(--text-secondary);
        }}

        .markdown-body li {{
            margin-bottom: 0.4rem;
        }}

        .markdown-body a {{
            color: var(--accent);
            text-decoration: none;
        }}

        .markdown-body a:hover {{
            text-decoration: underline;
        }}

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
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1.5rem;
            font-size: 0.9rem;
        }}

        .markdown-body th, .markdown-body td {{
            border: 1px solid var(--border-glass);
            padding: 0.75rem 1rem;
            text-align: left;
        }}

        .markdown-body th {{
            background: var(--bg-main);
            font-weight: 600;
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
            cursor: pointer;
            font-weight: 500;
            outline: none;
            color: var(--text-primary);
        }}

        /* Custom Showroom Visuals */
        .card {{
            background: var(--bg-main);
            border: 1px solid var(--border-glass);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .connections-visualizer {{
            display: flex;
            flex-direction: column;
            gap: 1rem;
            align-items: flex-start;
            padding: 1rem 0;
        }}

        .showroom-flow-node {{
            background: var(--bg-main);
            border: 1px solid var(--border-glass);
            border-radius: 8px;
            padding: 1rem 1.5rem;
            font-weight: 500;
            color: var(--text-primary);
            box-shadow: var(--shadow-sm);
        }}

        .showroom-flow-arrow {{
            color: var(--text-muted);
            font-size: 1rem;
            padding: 0.25rem 0;
        }}

        .footer {{
            text-align: center;
            color: var(--text-muted);
            font-size: 0.8rem;
            padding: 1rem;
        }}

        .footer a {{
            color: var(--accent);
            text-decoration: none;
            font-weight: 500;
        }}
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
                    <button class="tab-btn" onclick="switchTab('architecture')">Architecture Flow</button>
                    <button class="tab-btn" onclick="switchTab('quickstart')">Interactive Guide</button>
                </div>

                <!-- README TAB -->
                <div id="readme-tab" class="tab-content active">
                    <div id="readme-html" class="markdown-body"></div>
                </div>

                <!-- ARCHITECTURE TAB -->
                <div id="architecture-tab" class="tab-content">
                    <h2 style="color: #60a5fa; margin-bottom: 1.5rem;">System Architecture Diagram</h2>
                    <div class="card">
                        <div class="mermaid" style="background: transparent; display: flex; justify-content: center;">{mermaid_graph_str}</div>
                    </div>
                </div>

                <!-- QUICKSTART TAB -->
                <div id="quickstart-tab" class="tab-content">
                    <h2 style="color: #60a5fa; margin-bottom: 1rem;">Let's Get Started</h2>
                    <p style="margin-bottom: 1.5rem; color: var(--text-secondary);">Here is how the system connects step-by-step.</p>
                    
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
        const markdown = `{escaped_readme}`;
        document.getElementById('readme-html').innerHTML = marked.parse(markdown);

        mermaid.initialize({{ startOnLoad: false, theme: 'base' }});

        function switchTab(tabId) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.textContent.toLowerCase().includes(tabId));
            if (activeBtn) activeBtn.classList.add('active');

            const activeTab = document.getElementById(tabId + '-tab');
            if (activeTab) activeTab.classList.add('active');

            if (tabId === 'architecture') {{
                const mermaidEl = document.querySelector('.mermaid');
                if (mermaidEl && mermaidEl.textContent.trim() && mermaidEl.textContent.trim() !== 'graph TD') {{
                    mermaid.run({{ querySelector: '.mermaid' }});
                }}
            }}
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            const mermaidEl = document.querySelector('.mermaid');
            if (mermaidEl && mermaidEl.textContent.trim() && mermaidEl.textContent.trim() !== 'graph TD') {{
                mermaid.run({{ querySelector: '.mermaid' }});
            }}
        }});
    </script>
</body>
</html>
"""
        return html_content

    def _generate_showroom_flow_html(self, analysis):
        """Converts connections to visual stack blocks for the guide tab."""
        connections = analysis.get("connections", [])
        if not connections:
            return "<div class='card'>No data connections mapped for this project.</div>"
            
        nodes = []
        for c in connections:
            if c.get("from") not in nodes:
                nodes.append(c.get("from"))
            if c.get("to") not in nodes:
                nodes.append(c.get("to"))
                
        # Limit to reasonable sequence list
        html = []
        for idx, node in enumerate(nodes):
            html.append(f'<div class="showroom-flow-node">{node}</div>')
            if idx < len(nodes) - 1:
                html.append('<div class="showroom-flow-arrow">↓</div>')
                
        return "\n".join(html)
