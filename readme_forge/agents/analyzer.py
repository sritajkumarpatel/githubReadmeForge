import json
from readme_forge.llm import LLMClient
from readme_forge.agents.contracts import normalize_analysis


class AnalyzerAgent:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def analyze(self, scan_results):
        """Analyzes the scan results from the ReaderAgent and extracts deep structural facts,
        features, config, architecture layers, data models, and test coverage."""

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
            "  \"project_type\": \"One of: learning, poc, demo, library, application, cli, api, minimal, unknown. Choose the most accurate type.\",\n"
            "  \"project_type_reason\": \"Brief explanation of why this type was selected.\",\n"
            "  \"project_maturity\": \"One of: production, development, poc, unknown. Be honest about the project's current state.\",\n"
            "  \"classification\": {\n"
            "    \"primary_intent\": \"learning, poc, demo, library, application, cli, api, minimal, or unknown\",\n"
            "    \"delivery_surfaces\": [\"Any applicable values from: package, cli, api, ui\"],\n"
            "    \"confidence\": 0.0\n"
            "  },\n"
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
            "  \"data_models\": [\n"
            "    {\n"
            "      \"name\": \"ModelName\",\n"
            "      \"fields\": [\"field1\", \"field2\"],\n"
            "      \"description\": \"What this model represents in the domain\"\n"
            "    }\n"
            "  ],\n"
            "  \"installation_commands\": [\n"
            "    {\n"
            "      \"step\": \"1\",\n"
            "      \"command\": \"git clone https://github.com/...\",\n"
            "      \"description\": \"Clone the repository\"\n"
            "    }\n"
            "  ],\n"
            "  \"external_services\": [\"List of external APIs, databases, or third-party services the project integrates with\"],\n"
            "  \"test_coverage\": {\n"
            "    \"has_tests\": true,\n"
            "    \"framework\": \"pytest\",\n"
            "    \"test_count\": 0,\n"
            "    \"description\": \"Brief description of what is tested\"\n"
            "  },\n"
            "  \"architecture_layers\": [\n"
            "    {\n"
            "      \"layer\": \"Layer name (e.g. CLI Layer, API Layer, Business Logic, Data Layer)\",\n"
            "      \"files\": [\"file1.py\", \"directory/\"],\n"
            "      \"responsibility\": \"What this layer does and how it connects to others\"\n"
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
            "  ],\n"
            "  \"differentiators\": [\n"
            "    \"List 3-5 CONCRETE technical choices or claims that distinguish this project from competitors. Examples: 'Zero runtime dependencies', 'TypeScript-first', 'Single static binary', 'No new syntax'. Empty array if you cannot identify concrete differentiators.\"\n"
            "  ],\n"
            "  \"installation_methods\": [\n"
            "    {\n"
            "      \"name\": \"Method name (e.g. 'uv', 'pip', 'npm', 'docker')\",\n"
            "      \"command\": \"actual install command\",\n"
            "      \"description\": \"What this method does or when to use it\"\n"
            "    }\n"
            "  ],\n"
            "  \"recommended_style\": \"One of: reference, narrative, tutorial, showcase, minimal. Pick the style that best fits the project type.\",\n"
            "  \"has_visual_interface\": \"true if the project has a UI, dashboard, screenshots, or visual output. false otherwise.\",\n"
            "  \"ui_assets\": [\n"
            "    \"List of available image/screenshot paths that can be used as hero/demo content. Reference paths from the scan data if any.\"\n"
            "  ]\n"
            "}\n"
            "\n"
            "PROJECT TYPE GUIDELINES (Classify strictly using these rules):\n"
            "- learning: Tutorial repositories, exercise/practice directories, school homework, training guides, template/starter sandboxes, or simple demo projects. Detection signal: contains words like 'course', 'tutorial', 'practice', 'exercise', 'learn-', 'example-', or lacks formal packaging/production setup.\n"
            "- minimal: Small script utilities or single-file tools (1-2 source files overall, less than 200 lines). Avoid full application/cli categories for single utility files.\n"
            "- poc: Proof-of-concept, early draft implementation, or experimental prototypes where code is functional but incomplete/experimental.\n"
            "- demo: Showcase or demonstration repositories — polished enough to show off a concept or product to an audience but not meant as a reusable library or production system. Signaled by names containing 'demo', 'showcase', 'showroom', 'sample-app', or having very thin logic with a prominent front-end or landing page.\n"
            "- library: Reusable codebase components, helper packages, or modules intended to be imported by other projects (e.g. published to PyPI, npm, crates.io). Signaled by setup files (setup.py, pyproject.toml exports, package.json main/exports, Cargo.toml package).\n"
            "- cli: Terminal-based command-line interface utilities that parse flags and arguments (signaled by click, argparse, sys.argv, commander, etc.).\n"
            "- api: Backend API or web services defining endpoints, routing, and controller formats (signaled by Express, FastAPI, Flask, Django REST, REST controllers, etc.).\n"
            "- application: Full-stack, desktop, mobile, frontend, or distributed applications with user interfaces, workflows, database integrations, or complex setups.\n"
            "- unknown: Use this ONLY when there is genuinely insufficient code to classify (e.g. empty or near-empty repository with no source files).\n"
            "\n"
            "STRICT TYPE SCHEMAS:\n"
            "- tech_stack: MUST be a flat list of simple strings (e.g. [\"Python\", \"React\"]). NEVER include dictionaries or key/value objects.\n"
            "- external_services: MUST be a flat list of simple strings (e.g. [\"Gemini API\", \"PostgreSQL\"]). NEVER include dictionaries or key/value objects.\n"
            "\n"
            "PROJECT MATURITY CLASSIFICATION:\n"
            "Classify the project maturity honestly:\n"
            "- production: Stable, well-tested, production-ready. Has CI/CD, tests, documentation.\n"
            "- development: Active development, may have some rough edges. Has basic functionality working.\n"
            "- poc: Proof-of-concept, early prototype, or experiment. May be incomplete or non-functional.\n"
            "- unknown: Unable to determine maturity from available information.\n"
            "\n"
            "IMPORTANT RULES:\n"
            "- key_features: Extract every meaningful feature supported by the code. It is valid to return fewer than three or an empty array; never invent features to meet a quota.\n"
            "- api_endpoints: Only include if the project has HTTP/API routes. Leave as empty array if not applicable.\n"
            "- config_variables: Extract from .env files, environment variable reads in code (os.getenv, process.env), and CLI argument parsers.\n"
            "- cli_commands: Extract from argparse, click, commander, or similar CLI framework usage. Leave as empty array if not applicable.\n"
            "- problem_statement: Infer the pain point from what the tool does. Think about why someone would need this.\n"
            "- connections: Map the actual architectural flow between real components/files, not generic patterns.\n"
            "- data_models: Look for class definitions, Pydantic models, TypeScript interfaces, SQLAlchemy models, Zod schemas, or database schema files. If none exist, return empty array.\n"
            "- architecture_layers: DERIVE layer names from the actual directory structure and file names shown in the tree. Do NOT invent generic layer names — use what the code reveals.\n"
            "- installation_commands: Build the full installation sequence a user would need to run from scratch (clone → install deps → configure → run).\n"
            "- external_services: Use the external_api_calls data provided to identify real services. Supplement with imports/environment variables you see in the code.\n"
            "- test_coverage: Use the test_signals data provided. If has_tests is true, describe what the tests are validating based on the sample_test content.\n"
            "\n"
            "EXTRACT SPECIFICS - DO NOT USE GENERIC DESCRIPTIONS:\n"
            "- tech_stack: List SPECIFIC frameworks, libraries, and tools (e.g., 'FastMCP', 'UV', 'Pydantic', 'MCP Inspector', 'Uvicorn'). Do NOT just say 'Python' when the project uses 'FastMCP' or 'Streamable HTTP'.\n"
            "- project_persona: Be specific about what the project actually does. 'A learning project for MCP servers' is better than 'A software application'.\n"
            "- key_features: Describe what the specific code does. 'Weather data fetching via MCP protocol' is better than 'Data retrieval feature'.\n"
            "\n"
            "STYLE RECOMMENDATION:\n"
            "- recommended_style: Choose the README style that best matches the project:\n"
            "  * 'reference' — for libraries, CLIs, SDKs, APIs (Axios, FastAPI, ripgrep pattern)\n"
            "  * 'narrative' — for products, frameworks, applications (Supabase, AppFlowy, Plausible pattern)\n"
            "  * 'tutorial' — for learning resources, awesome-lists, teaching repos (build-your-own-x pattern)\n"
            "  * 'showcase' — for products with a strong visual interface (AppFlowy, Phaser pattern)\n"
            "  * 'minimal' — for small utilities and minimal scripts (jq, Three.js pattern)\n"
            "- has_visual_interface: true if the project has a UI, dashboard, screenshots, or visual output\n"
            "- ui_assets: list of relevant image paths from the codebase (the Writer will reference these in the README)\n"
            "\n"
            "DIFFERENTIATORS:\n"
            "- differentiators: List 3-5 CONCRETE technical choices that distinguish this project. Examples: 'TypeScript-first', 'Zero runtime dependencies', 'Single static binary', 'OpenAPI-compatible', 'No new syntax to learn'. If you cannot identify concrete differentiators, return an empty array.\n"
            "\n"
            "INSTALLATION:\n"
            "- installation_methods: List ALL the install commands a user could use (from package.json scripts, pyproject.toml scripts, Makefile, README, Dockerfile, etc.). Include the package manager name, the actual command, and a short description.\n"
        )

        # Prepare character budget based on model provider
        provider = getattr(self.llm_client, "provider", "mock").lower()
        budget = 320_000  # Default
        if provider == "gemini":
            budget = 3_600_000
        elif provider == "openai":
            budget = 320_000
        elif provider == "claude":
            budget = 600_000
        elif provider == "ollama":
            budget = 24_000
        elif provider == "mock":
            budget = 4_000_000

        # Prepare user prompt with all codebase data
        tree_text = scan_results.get("tree", "")
        configs_text = ""
        for fn, contents in scan_results.get("configs", {}).items():
            configs_text += f"--- FILE: {fn} ---\n{contents}\n\n"

        existing_readme = scan_results.get("existing_readme", "")

        narrative_hints_text = ""
        for hint in scan_results.get("narrative_hints", []):
            narrative_hints_text += f"- {hint}\n"

        test_signals = scan_results.get("test_signals", {})
        test_signals_text = (
            f"- Test framework detected: {test_signals.get('framework', 'unknown')}\n"
            f"- Number of test files found: {test_signals.get('file_count', 0)}\n"
            f"- Has tests: {test_signals.get('has_tests', False)}\n"
        )
        if test_signals.get("sample_test"):
            test_signals_text += f"- Sample test content: {test_signals.get('sample_test')}\n"

        version_info = scan_results.get("version_info", {})
        version_text = ""
        if version_info.get("version"):
            version_text += f"- Current version: {version_info.get('version')}\n"
        if version_info.get("changelog_snippet"):
            version_text += f"- Recent changelog:\n{version_info.get('changelog_snippet')[:800]}\n"

        external_apis = scan_results.get("external_api_calls", [])
        external_apis_text = ""
        if external_apis:
            external_apis_text = "Outbound HTTP calls detected to these domains:\n"
            for domain in external_apis:
                external_apis_text += f"  - {domain}\n"

        hero_assets = scan_results.get("hero_assets", [])
        hero_assets_text = ""
        if hero_assets:
            hero_assets_text = "Visual assets available in the repository (use as hero/demo if has_visual_interface):\n"
            for asset in hero_assets:
                hero_assets_text += f"  - {asset['path']} ({asset['kind']})\n"

        # Calculate budget for code context
        fixed_len = (
            len(tree_text)
            + len(existing_readme)
            + len(configs_text)
            + len(narrative_hints_text)
            + len(test_signals_text)
            + len(version_text)
            + len(external_apis_text)
            + 2000  # Prompt system template buffer
        )
        remaining_budget = budget - fixed_len

        code_context_text = ""
        context_truncated = False
        for path, contents in scan_results.get("code_context", {}).items():
            file_text = f"--- FILE: {path} ---\n{contents}\n\n"
            if len(code_context_text) + len(file_text) < remaining_budget:
                code_context_text += file_text
            else:
                context_truncated = True

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

        user_prompt += (
            f"Here are test signals detected in the codebase:\n"
            f"{test_signals_text}\n\n"
        )

        if version_text:
            user_prompt += f"Version and changelog information:\n{version_text}\n\n"

        if external_apis_text:
            user_prompt += f"{external_apis_text}\n\n"

        if hero_assets_text:
            user_prompt += f"{hero_assets_text}\n\n"

        user_prompt += (
            "Please analyze these resources and return the comprehensive JSON analysis. "
            "A repository may expose multiple delivery surfaces (for example a package plus CLI plus API). "
            "Report all applicable surfaces rather than forcing them into one label."
        )

        raw_response = self.llm_client.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_format_json=True,
        )

        # Clean response if the model wrapped it in markdown code blocks despite instructions
        clean_response = raw_response.strip()
        if clean_response.startswith("```"):
            lines = clean_response.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].startswith("```"):
                lines = lines[:-1]
            clean_response = "\n".join(lines).strip()

        try:
            analysis_data = json.loads(clean_response)
            return normalize_analysis(analysis_data, scan_results, context_truncated=context_truncated)
        except Exception as e:
            print(f"[Analyzer] Warning: Failed to parse LLM analysis JSON: {e}")
            # Do not fabricate a generic product description when analysis fails.
            # The normalizer still supplies deterministic repository classification.
            return normalize_analysis({}, scan_results, analysis_complete=False, context_truncated=context_truncated)
