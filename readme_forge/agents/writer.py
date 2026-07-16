from pathlib import Path
from readme_forge.llm import LLMClient
from readme_forge.hero_generator import HeroGenerator

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
        
        # 1. Generate SVGs if output_dir is specified
        project_name = self._parse_project_name(target_path_or_url or scan_results.get("path"))
        if output_dir:
            try:
                assets_dir = Path(output_dir) / "assets" / "readme"
                generator = HeroGenerator(
                    project_name=project_name,
                    project_persona=analysis.get("project_persona"),
                    tech_stack=analysis.get("tech_stack", [])
                )
                generator.generate(assets_dir)
            except Exception as e:
                print(f"[Writer] Warning: Failed to generate SVG hero banners: {e}")

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
                "- Use visual SVG shields/badges at the top for tech stack and metadata details.\n"
                "- Incorporate visual clues, icons, and formatted callout blocks.\n"
                "- Use collapsible `<details>` blocks to keep configuration tables clean.\n"
                "- Create engaging layouts with rich lists and visual highlights."
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
            f"Formatting Theme instructions:\n{style_instruction}\n\n"
            f"Language settings:\n{lang_instruction}\n\n"
            "CRITICAL GUARDRAIL:\n"
            "If the user custom answers or prompt demands anything unrelated to documenting this project repository "
            "(such as writing standalone calculator scripts, general Python coding tasks, math solver programs, or unrelated topics), "
            "you MUST refuse the request and respond with exactly: 'Refusal: This request is unrelated to README generation. Please ask documentation-related questions.'\n\n"
            "OTHERWISE, write the complete README markdown file using the following **Narrative-Driven Layout Structure**:\n\n"
            "1. **Hero Banner**: If not minimalist theme, embed the responsive dark/light hero banner:\n"
            "   <picture>\n"
            "     <source media=\"(prefers-color-scheme: dark)\" srcset=\"assets/readme/hero-dark.svg\">\n"
            "     <source media=\"(prefers-color-scheme: light)\" srcset=\"assets/readme/hero-light.svg\">\n"
            "     <img alt=\"Project Hero Banner\" src=\"assets/readme/hero-light.svg\" width=\"100%\">\n"
            "   </picture>\n"
            f"2. **Language Switcher**: If the language switcher is defined below, insert it at the very top (right-aligned or centered):\n"
            f"   {lang_switcher}\n"
            "3. **Title Block**: Center-aligned project name with a bold tagline and shields.io badges for tech stack, license, etc.\n\n"
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
            "7. **Features**: Create a visually rich feature list with:\n"
            "   - An emoji icon for each feature\n"
            "   - A bold feature name as a sub-heading\n"
            "   - A 2-3 sentence description explaining what it does and why it matters\n"
            "   - Group related features logically\n"
            "   - Use the `key_features` from analysis data\n\n"
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
            f"File Tree Structure:\n{scan_results.get('tree')}\n\n"
            f"Tech Stack analyzed: {analysis.get('tech_stack')}\n"
            f"Project Persona: {analysis.get('project_persona')}\n"
            f"Problem Statement: {analysis.get('problem_statement', 'Not specified')}\n"
            f"Solution Narrative: {analysis.get('solution_narrative', 'Not specified')}\n"
            f"Component Flow Connections: {analysis.get('connections')}\n\n"
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

    def generate_showroom_html(self, readme_markdown, analysis):
        """Generates a premium glassmorphic Showroom HTML file that renders the README dynamically and includes rich visual tabs/animations."""
        
        # We can construct a highly interactive static HTML template.
        # It imports Mermaid.js and marked.js (markdown parser) via CDN so it loads dynamically,
        # and styles it with a sleek, glowing dark glassmorphism CSS interface, tabs, and copy-buttons.
        
        escaped_readme = readme_markdown.replace("`", "\\`").replace("$", "\\$")
        
        tech_badges = ""
        for tech in analysis.get("tech_stack", []):
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
            --bg-color: #0b0f19;
            --card-bg: rgba(22, 29, 49, 0.6);
            --border-color: rgba(255, 255, 255, 0.08);
            --accent-color: #3b82f6;
            --accent-glow: rgba(59, 130, 246, 0.4);
            --text-primary: #f3f4f6;
            --text-secondary: #9ca3af;
        }}
        
        * {{
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }}

        body {{
            font-family: 'Outfit', sans-serif;
            background-color: var(--bg-color);
            color: var(--text-primary);
            min-height: 100vh;
            background-image: 
                radial-gradient(at 0% 0%, rgba(59, 130, 246, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.15) 0px, transparent 50%);
            padding: 2rem;
            display: flex;
            justify-content: center;
        }}

        .container {{
            width: 100%;
            max-width: 1100px;
            display: flex;
            flex-direction: column;
            gap: 2rem;
        }}

        header {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            padding: 2.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            position: relative;
            overflow: hidden;
        }}

        header::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
        }}

        h1 {{
            font-size: 2.8rem;
            font-weight: 800;
            background: linear-gradient(to right, #3b82f6, #a78bfa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}

        .subtitle {{
            color: var(--text-secondary);
            font-size: 1.2rem;
            margin-bottom: 1.5rem;
        }}

        .tech-badges {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}

        .tech-badge {{
            background: rgba(59, 130, 246, 0.15);
            border: 1px solid rgba(59, 130, 246, 0.3);
            color: #93c5fd;
            padding: 0.3rem 0.8rem;
            border-radius: 50px;
            font-size: 0.85rem;
            font-weight: 600;
            letter-spacing: 0.05em;
        }}

        main {{
            display: grid;
            grid-template-columns: 1fr;
            gap: 2rem;
        }}

        .tabs-container {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border-color);
            border-radius: 16px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
            overflow: hidden;
        }}

        .tab-bar {{
            display: flex;
            border-bottom: 1px solid var(--border-color);
            background: rgba(0, 0, 0, 0.2);
            padding: 0.5rem 1rem 0;
        }}

        .tab-btn {{
            background: none;
            border: none;
            color: var(--text-secondary);
            padding: 1rem 1.5rem;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            border-radius: 8px 8px 0 0;
            transition: all 0.3s ease;
            position: relative;
        }}

        .tab-btn:hover {{
            color: var(--text-primary);
        }}

        .tab-btn.active {{
            color: var(--accent-color);
            background: rgba(22, 29, 49, 0.8);
        }}

        .tab-btn.active::after {{
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 3px;
            background: var(--accent-color);
            box-shadow: 0 0 10px var(--accent-glow);
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
            line-height: 1.6;
        }}
        
        .markdown-body h2 {{
            font-size: 1.8rem;
            margin-top: 2rem;
            margin-bottom: 1rem;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 0.5rem;
            color: #60a5fa;
        }}

        .markdown-body h3 {{
            font-size: 1.4rem;
            margin-top: 1.5rem;
            margin-bottom: 0.8rem;
            color: #a78bfa;
        }}

        .markdown-body p {{
            margin-bottom: 1.2rem;
            color: #d1d5db;
        }}

        .markdown-body ul, .markdown-body ol {{
            margin-left: 2rem;
            margin-bottom: 1.2rem;
            color: #d1d5db;
        }}

        .markdown-body li {{
            margin-bottom: 0.5rem;
        }}

        .markdown-body pre {{
            background: #0f172a;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1.2rem;
            margin-bottom: 1.5rem;
            overflow-x: auto;
            position: relative;
        }}

        .markdown-body code {{
            font-family: 'JetBrains Mono', monospace;
            font-size: 0.9rem;
        }}

        .markdown-body :not(pre) > code {{
            background: rgba(255, 255, 255, 0.08);
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            color: #f472b6;
        }}

        .markdown-body table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1.5rem;
        }}

        .markdown-body th, .markdown-body td {{
            border: 1px solid var(--border-color);
            padding: 0.75rem;
            text-align: left;
        }}

        .markdown-body th {{
            background-color: rgba(255, 255, 255, 0.03);
            font-weight: 600;
        }}

        .markdown-body blockquote {{
            border-left: 4px solid var(--accent-color);
            background: rgba(59, 130, 246, 0.05);
            padding: 1rem 1.5rem;
            margin-bottom: 1.5rem;
            border-radius: 0 8px 8px 0;
            color: #93c5fd;
        }}

        .markdown-body details {{
            background: rgba(0, 0, 0, 0.2);
            border: 1px solid var(--border-color);
            border-radius: 8px;
            padding: 1rem;
            margin-bottom: 1.2rem;
        }}

        .markdown-body summary {{
            cursor: pointer;
            font-weight: 600;
            outline: none;
            color: #e5e7eb;
        }}

        .markdown-body summary:hover {{
            color: var(--accent-color);
        }}

        /* Custom Showroom Visuals */
        .card {{
            background: rgba(0, 0, 0, 0.15);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1.5rem;
        }}

        .connections-visualizer {{
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            align-items: center;
            padding: 2rem;
        }}

        .showroom-flow-node {{
            background: linear-gradient(135deg, #1e293b, #0f172a);
            border: 1px solid #3b82f6;
            box-shadow: 0 0 15px rgba(59, 130, 246, 0.2);
            border-radius: 8px;
            padding: 1rem 1.5rem;
            width: 250px;
            text-align: center;
            font-weight: 600;
            position: relative;
        }}

        .showroom-flow-arrow {{
            color: #8b5cf6;
            font-size: 1.5rem;
            animation: bounce 2s infinite;
        }}

        @keyframes bounce {{
            0%, 100% {{ transform: translateY(0); }}
            50% {{ transform: translateY(5px); }}
        }}

        .footer {{
            text-align: center;
            color: var(--text-secondary);
            font-size: 0.85rem;
            margin-top: 1rem;
            padding: 1.5rem;
        }}

        .footer a {{
            color: var(--accent-color);
            text-decoration: none;
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Project Showroom</h1>
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
            Generated with 🛠️ <a href="https://github.com/user/githubReadmeForge" target="_blank">githubReadmeForge</a> - Intelligent Agentic README Architect.
        </div>
    </div>

    <script>
        // Set up markdown content
        const markdown = `{escaped_readme}`;
        document.getElementById('readme-html').innerHTML = marked.parse(markdown);

        // Initialize mermaid
        mermaid.initialize({{ startOnLoad: false, theme: 'dark' }});

        // Tab Switcher Logic
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));

            const activeBtn = Array.from(document.querySelectorAll('.tab-btn')).find(btn => btn.textContent.toLowerCase().includes(tabId));
            if (activeBtn) activeBtn.classList.add('active');
            
            const activeTab = document.getElementById(tabId + '-tab');
            if (activeTab) activeTab.classList.add('active');

            if (tabId === 'architecture') {{
                mermaid.run({{
                    querySelector: '.mermaid'
                }});
            }}
        }}
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
