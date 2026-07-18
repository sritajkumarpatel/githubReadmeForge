import os
import sys
import json
import argparse
import urllib.parse
import shutil
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add project root to sys.path so we can import readme_forge
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from readme_forge import load_env_file
load_env_file()

from readme_forge.llm import LLMClient
from readme_forge.agents.reader import ReaderAgent
from readme_forge.agents.analyzer import AnalyzerAgent
from readme_forge.agents.writer import WriterAgent
from readme_forge.agents.contracts import normalize_analysis, build_documentation_plan

class APIRequestHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        # Enable CORS for local testing/development
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def do_GET(self):
        # Serve static assets from the 'web' folder or output folder
        parsed_path = urllib.parse.urlparse(self.path)
        clean_path = parsed_path.path

        if clean_path == "/api/health":
            self._send_json({"status": "ok", "message": "githubReadmeForge Web Server is healthy."})
            return

        if clean_path == "/" or clean_path == "/index.html":
            file_path = project_root / "web" / "index.html"
        elif clean_path.startswith("/assets/"):
            # Check any draft directories, then output directory, then web directory
            draft_file = None
            import glob
            for d_dir in sorted(glob.glob(str(project_root / ".readme_forge_draft_*"))):
                cand = Path(d_dir) / clean_path.lstrip("/")
                if cand.exists():
                    draft_file = cand
                    break
            
            output_path = project_root / "readme_forge_output" / clean_path.lstrip("/")
            if draft_file:
                file_path = draft_file
            elif output_path.exists():
                file_path = output_path
            else:
                file_path = project_root / "web" / clean_path.lstrip("/")
        else:
            # Strip leading slash and find file
            file_path = project_root / "web" / clean_path.lstrip("/")

        # Prevent directory traversal attacks
        try:
            resolved_path = file_path.resolve()
            web_dir_resolved = (project_root / "web").resolve()
            output_dir_resolved = (project_root / "readme_forge_output").resolve()
            is_valid_draft = str(resolved_path).startswith(str((project_root / ".readme_forge_draft_").resolve()))
            if (not str(resolved_path).startswith(str(web_dir_resolved)) and 
                not str(resolved_path).startswith(str(output_dir_resolved)) and
                not is_valid_draft):
                self.send_error(403, "Access Denied")
                return
        except Exception:
            self.send_error(404, "File Not Found")
            return

        if resolved_path.exists() and resolved_path.is_file():
            self.send_response(200)

            # Content types
            suffix = resolved_path.suffix.lower()
            if suffix == ".html":
                self.send_header("Content-Type", "text/html; charset=utf-8")
            elif suffix == ".css":
                self.send_header("Content-Type", "text/css; charset=utf-8")
            elif suffix == ".js":
                self.send_header("Content-Type", "application/javascript; charset=utf-8")
            elif suffix == ".json":
                self.send_header("Content-Type", "application/json; charset=utf-8")
            elif suffix == ".svg":
                self.send_header("Content-Type", "image/svg+xml; charset=utf-8")
            else:
                self.send_header("Content-Type", "application/octet-stream")
                
            self.end_headers()
            with open(resolved_path, "rb") as f:
                self.wfile.write(f.read())
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        parsed_path = urllib.parse.urlparse(self.path)
        clean_path = parsed_path.path

        if clean_path == "/api/analyze":
            self._handle_analyze()
        elif clean_path == "/api/generate":
            self._handle_generate()
        elif clean_path == "/api/models":
            self._handle_models()
        elif clean_path == "/api/export":
            self._handle_export()
        elif clean_path == "/api/drift":
            self._handle_drift()
        else:
            self.send_error(404, "API Endpoint Not Found")

    def _handle_models(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            req_body = json.loads(post_data) if post_data else {}
        except Exception as e:
            self._send_json({"success": False, "error": f"Invalid JSON body: {e}"}, 400)
            return

        provider = req_body.get("provider", "")
        api_key = req_body.get("api_key")
        base_url = req_body.get("base_url")

        if api_key == "••••••••":
            api_key = None

        # Check if we have an API key or if the provider doesn't require one (or has env key)
        effective_key = api_key
        if not effective_key:
            dummy_client = LLMClient(provider=provider, api_key=None, base_url=base_url)
            effective_key = dummy_client.api_key

        if not effective_key and provider not in ("ollama", "opencode", "mock"):
            self._send_json({"success": False, "error": "API key is required"}, 400)
            return

        llm_client = LLMClient(provider=provider, api_key=api_key, base_url=base_url)
        models = llm_client.get_available_models()

        if isinstance(models, dict) and "error" in models:
            self._send_json({"success": False, "error": models["error"]}, 400)
            return

        self._send_json({"success": True, "models": models})

    def _handle_analyze(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            req_body = json.loads(post_data) if post_data else {}
        except Exception as e:
            self._send_json({"success": False, "error": f"Invalid JSON body: {e}"}, 400)
            return

        target_path = req_body.get("path", ".").strip()
        provider = req_body.get("provider", "mock")
        model = req_body.get("model")
        api_key = req_body.get("api_key")
        base_url = req_body.get("base_url")

        if api_key == "••••••••":
            api_key = None

        if not target_path:
            self._send_json({"success": False, "error": "Repository path or URL is required."}, 400)
            return

        reader = None
        try:
            reader = ReaderAgent(target_path)
            reader.setup()
            scan_results = reader.scan_codebase()

            # Instantiate LLM client and analyze
            llm_client = LLMClient(provider=provider, model=model, api_key=api_key, base_url=base_url)
            analyzer = AnalyzerAgent(llm_client)
            analysis = analyzer.analyze(scan_results)
            doc_plan = build_documentation_plan(analysis)

            # Generate completeness score and deterministic gaps
            score, deterministic_gaps = self._calculate_readme_score(analysis, scan_results)

            # Merge deterministic gaps into analyzer's improvements so the UI Gaps Table
            # shows exactly why points were deducted.
            existing_improvements = analysis.get("improvements", []) or []
            max_existing_id = 0
            for imp in existing_improvements:
                try:
                    max_existing_id = max(max_existing_id, int(imp.get("id", "0") or "0"))
                except (TypeError, ValueError):
                    pass
            for idx, gap in enumerate(deterministic_gaps):
                gap["id"] = str(max_existing_id + idx + 1)
                gap.pop("deduction", None)
            merged_improvements = list(existing_improvements) + deterministic_gaps
            analysis["improvements"] = merged_improvements

            self._send_json({
                "success": True,
                "score": score,
                "score_gaps": deterministic_gaps,
                "scan": scan_results,
                "analysis": analysis,
                "doc_plan": doc_plan
            })
        except FileNotFoundError as e:
            self._send_json({
                "success": False,
                "error_type": "scan_error",
                "error": f"Path not found: {e}",
                "hint": "Check that the path exists and is readable."
            }, 404)
        except RuntimeError as e:
            error_msg = str(e)
            if "Authentication failed" in error_msg or "credentials" in error_msg.lower():
                self._send_json({
                    "success": False,
                    "error_type": "auth_error",
                    "error": error_msg,
                    "hint": "Check that your GitHub credentials or access token are valid for this repository."
                }, 401)
            elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                self._send_json({
                    "success": False,
                    "error_type": "clone_error",
                    "error": error_msg,
                    "hint": "Verify the repository URL is correct and publicly accessible."
                }, 404)
            else:
                self._send_json({
                    "success": False,
                    "error_type": "scan_error",
                    "error": error_msg,
                    "hint": "An error occurred while scanning the repository."
                }, 500)
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            # Classify common LLM errors
            if "api key" in error_msg.lower() or "apikey" in error_msg.lower() or "401" in error_msg:
                self._send_json({
                    "success": False,
                    "error_type": "auth_error",
                    "error": "Invalid or missing API key.",
                    "hint": "Check your API key in the provider settings."
                }, 401)
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                self._send_json({
                    "success": False,
                    "error_type": "rate_limit",
                    "error": "API rate limit or quota exceeded.",
                    "hint": "Wait a moment and try again, or upgrade your API plan."
                }, 429)
            else:
                self._send_json({
                    "success": False,
                    "error_type": "server_error",
                    "error": error_msg,
                    "hint": "An unexpected error occurred during analysis."
                }, 500)
        finally:
            if reader:
                reader.cleanup()

    def _handle_generate(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            req_body = json.loads(post_data) if post_data else {}
        except Exception as e:
            self._send_json({"success": False, "error": f"Invalid JSON body: {e}"}, 400)
            return

        scan_results = req_body.get("scan")
        analysis = req_body.get("analysis")
        provider = req_body.get("provider")
        model = req_body.get("model")
        api_key = req_body.get("api_key")
        base_url = req_body.get("base_url")
        custom_answers = req_body.get("custom_answers")
        readme_style = req_body.get("style", "visual_rich")
        lang = req_body.get("lang", "en")

        if api_key == "••••••••":
            api_key = None

        if not scan_results or not analysis:
            self._send_json({"success": False, "error": "Analysis context is missing."}, 400)
            return

        if not isinstance(scan_results, dict) or not isinstance(analysis, dict):
            self._send_json({"success": False, "error": "Analysis context must be a JSON object."}, 400)
            return

        # Browser clients can submit a saved analysis payload directly. Normalize
        # it here too, so the Writer receives the same contract as the CLI flow.
        analysis = normalize_analysis(
            analysis,
            scan_results,
            analysis_complete=bool(analysis.get("analysis_complete", True)),
        )

        # Backend Guardrails: check for off-topic requests (e.g. asking to write separate coding programs)
        if custom_answers:
            lower_answers = custom_answers.lower()
            off_topic_indicators = [
                "write a program", "write a function", "write code to", "write a script",
                "sum program", "calculator program", "write a sum", "solve this", "math program"
            ]
            if any(indicator in lower_answers for indicator in off_topic_indicators):
                self._send_json({
                    "success": False,
                    "error": "Guardrail rejection: This agent is strictly designed to help set up project READMEs. Please ask documentation-related questions."
                }, 400)
                return



        try:
            llm_client = LLMClient(provider=provider, model=model, api_key=api_key, base_url=base_url)
            writer = WriterAgent(llm_client)

            # Determine output_dir (always save drafts into a short-lived draft folder).
            # The draft is kept just long enough to serve any static assets (SVGs) the
            # web UI may request after generation. A cleanup pass on startup removes
            # leftover drafts from previous runs.
            target_path = scan_results.get("path", ".")
            import uuid
            draft_id = f".readme_forge_draft_{uuid.uuid4().hex[:8]}"
            draft_dir = Path(project_root / draft_id)
            draft_dir.mkdir(parents=True, exist_ok=True)
            output_dir = draft_dir

            brief = req_body.get("brief")
            readme_md = writer.generate_readme(
                scan_results=scan_results,
                analysis=analysis,
                interactive_answers=custom_answers,
                style=readme_style,
                output_dir=output_dir,
                target_path_or_url=target_path,
                lang=lang,
                brief=brief
            )
            # Save README.md in the draft area
            (draft_dir / "README.md").write_text(readme_md, encoding="utf-8")

            self._send_json({
                "success": True,
                "readme": readme_md,
                "visual_assets": analysis.get("visual_assets", {}),
                "draft_id": draft_id
            })
        except Exception as e:
            import traceback
            traceback.print_exc()
            error_msg = str(e)
            if "api key" in error_msg.lower() or "apikey" in error_msg.lower() or "401" in error_msg:
                self._send_json({
                    "success": False,
                    "error_type": "auth_error",
                    "error": "Invalid or missing API key.",
                    "hint": "Check your API key in the provider settings panel."
                }, 401)
            elif "quota" in error_msg.lower() or "rate limit" in error_msg.lower():
                self._send_json({
                    "success": False,
                    "error_type": "rate_limit",
                    "error": "API rate limit or quota exceeded.",
                    "hint": "Wait a moment and try again, or upgrade your API plan."
                }, 429)
            elif "max_tokens" in error_msg.lower() or "context length" in error_msg.lower():
                self._send_json({
                    "success": False,
                    "error_type": "token_limit",
                    "error": "The repository is too large for the selected model's context window.",
                    "hint": "Try a model with a larger context window, or use a smaller repository."
                }, 500)
            elif "timed out after" in error_msg.lower() or "could not connect" in error_msg.lower():
                self._send_json({
                    "success": False,
                    "error_type": "provider_error",
                    "error": error_msg,
                    "hint": "Check that your LLM provider is reachable and try again."
                }, 504)
            else:
                self._send_json({
                    "success": False,
                    "error_type": "generation_error",
                    "error": error_msg,
                    "hint": "An unexpected error occurred during README generation."
                }, 500)
        finally:
            # Clean up any draft directories that are older than 1 hour.
            # The current draft is kept so the web UI can fetch SVG assets right
            # after generation. Stale drafts from previous sessions are removed.
            import glob
            now = time.time()
            for old_draft in glob.glob(str(project_root / ".readme_forge_draft_*")):
                try:
                    age = now - Path(old_draft).stat().st_mtime
                    if age > 3600:  # 1 hour
                        shutil.rmtree(old_draft, ignore_errors=True)
                except Exception:
                    pass

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

    def _calculate_readme_score(self, analysis, scan_results):
        """Calculates a visual completeness rating out of 100 based on structural codebase scanning and analysis.

        Returns:
            tuple: (score, gap_items) where gap_items is a list of dicts describing each deduction.
        """
        existing_readme = scan_results.get("existing_readme", "").strip()
        if not existing_readme:
            return 10, [{
                "id": "0",
                "title": "No existing README found",
                "description": "This project has no README.md file. Generating a new one is required.",
                "type": "Structure"
            }]

        score = 100
        readme_lower = existing_readme.lower()
        gap_items = []
        gap_id = 0

        def add_gap(title, description, gap_type, deduction):
            nonlocal score, gap_id
            gap_id += 1
            score -= deduction
            gap_items.append({
                "id": str(gap_id),
                "title": title,
                "description": description,
                "type": gap_type,
                "deduction": deduction
            })

        # 1. Check for visual elements (images, svgs, or mermaid diagrams)
        has_visuals = ("<img" in readme_lower or "![" in readme_lower or "```mermaid" in readme_lower)
        if not has_visuals:
            add_gap(
                "Missing visual elements",
                "The README does not contain any images, badges, or Mermaid diagrams. Visuals increase engagement and clarify architecture.",
                "Visual",
                20
            )

        # 2. Check for code examples / usage block
        has_usage = ("usage" in readme_lower or "quick start" in readme_lower or "getting started" in readme_lower)
        if not has_usage:
            add_gap(
                "Missing usage/quick-start section",
                "The README lacks a 'Usage' or 'Quick Start' section. New users need a clear path to run the project.",
                "Documentation",
                20
            )

        # 3. Check for installation block
        has_install = ("install" in readme_lower or "setup" in readme_lower)
        if not has_install:
            add_gap(
                "Missing installation instructions",
                "The README does not include an 'Installation' or 'Setup' section with concrete steps.",
                "Documentation",
                20
            )

        # 4. Check for configuration / environment variables
        has_config = any(term in readme_lower for term in ("config", "env", "port", "key"))
        if not has_config:
            add_gap(
                "Missing configuration documentation",
                "The README has no documented environment variables, config options, or settings.",
                "Configuration",
                10
            )

        # 5. Check for license / contributing
        has_license = ("license" in readme_lower or "mit" in readme_lower or "apache" in readme_lower)
        if not has_license:
            add_gap(
                "Missing license/contributing section",
                "The README does not mention a License or Contributing guide. Open-source projects should clarify terms.",
                "Legal",
                10
            )

        # Also deduct for improvements identified by analyzer
        improvements = analysis.get("improvements", [])
        if improvements:
            deduction = min(20, len(improvements) * 5)
            if deduction > 0:
                gap_id += 1
                gap_items.append({
                    "id": str(gap_id),
                    "title": f"{len(improvements)} AI-identified improvement(s)",
                    "description": f"The analyzer identified {len(improvements)} additional areas for improvement across structure, examples, or clarity.",
                    "type": "AI Analysis",
                    "deduction": deduction
                })
                score -= deduction

        return max(15, min(score, 100)), gap_items

    def _handle_export(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            req_body = json.loads(post_data) if post_data else {}
        except Exception as e:
            self._send_json({"success": False, "error": f"Invalid JSON body: {e}"}, 400)
            return

        target_path = req_body.get("path")
        if not target_path or not isinstance(target_path, str):
            target_path = "."
        target_path = target_path.strip()
        target_dir = Path(target_path).resolve()
        draft_id = req_body.get("draft_id", ".readme_forge_draft")
        draft_dir = Path(project_root / draft_id).resolve()

        if not draft_dir.exists() or not (draft_dir / "README.md").exists():
            self._send_json({"success": False, "error": "No draft content found to export. Generate a draft first."}, 400)
            return

        try:
            # 1. Copy README.md
            target_readme = target_dir / "README.md"
            import shutil
            shutil.copy2(draft_dir / "README.md", target_readme)

            # 2. Copy assets folder if it exists
            draft_assets = draft_dir / "assets" / "readme"
            if draft_assets.exists():
                target_assets = target_dir / "assets" / "readme"
                target_assets.mkdir(parents=True, exist_ok=True)
                for item in draft_assets.iterdir():
                    if item.is_file():
                        shutil.copy2(item, target_assets / item.name)

            self._send_json({"success": True, "message": "Draft exported successfully."})
        except Exception as e:
            self._send_json({"success": False, "error": f"Failed to export files: {e}"}, 500)

    def _handle_drift(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            req_body = json.loads(post_data) if post_data else {}
        except Exception as e:
            self._send_json({"success": False, "error": f"Invalid JSON body: {e}"}, 400)
            return

        scan_results = req_body.get("scan")
        analysis = req_body.get("analysis")
        target_path = req_body.get("path", ".").strip()

        if not scan_results or not analysis:
            self._send_json({"success": False, "error": "Analysis context is required for drift detection."}, 400)
            return

        try:
            from readme_forge.agents.drift import DriftDetector
            detector = DriftDetector(target_path)

            # Always prefer the README content already captured in scan_results.
            # For remote repos the clone is deleted by the time drift is called,
            # so reading from disk would always fail.
            existing_readme = (scan_results.get("existing_readme") or "").strip()
            if existing_readme:
                drifts = detector.detect_from_content(existing_readme, scan_results, analysis)
            else:
                drifts = detector.detect(scan_results, analysis)

            self._send_json({
                "success": True,
                "drift": drifts
            })
        except Exception as e:
            self._send_json({"success": False, "error": f"Drift detection failed: {e}"}, 500)


def run_server(port=8080):
    # Ensure web folder exists
    Path(project_root / "web").mkdir(exist_ok=True)
    
    # Startup cleanup of stale temp clones
    import glob
    import shutil
    for stale in glob.glob("/tmp/readme_forge_clone_*"):
        shutil.rmtree(stale, ignore_errors=True)

    server_address = ('', port)
    httpd = HTTPServer(server_address, APIRequestHandler)
    print(f"==================================================")
    print(f"🛠️ githubReadmeForge Web Server Running on port {port}")
    print(f"👉 Open http://localhost:{port} in your browser.")
    print(f"==================================================")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping web server...")
        httpd.server_close()
        print("Server stopped.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the githubReadmeForge API server.")
    parser.add_argument("--port", type=int, default=8080, help="Port to host server (default: 8080)")
    args = parser.parse_args()
    run_server(args.port)
