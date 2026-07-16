import os
import sys
import json
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

# Add project root to sys.path so we can import readme_forge
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from readme_forge.llm import LLMClient
from readme_forge.agents.reader import ReaderAgent
from readme_forge.agents.analyzer import AnalyzerAgent
from readme_forge.agents.writer import WriterAgent

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

        if clean_path == "/" or clean_path == "/index.html":
            file_path = project_root / "web" / "index.html"
        elif clean_path.startswith("/assets/"):
            # Check output directory first, then web directory
            output_path = project_root / "readme_forge_output" / clean_path.lstrip("/")
            if output_path.exists():
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
            if not str(resolved_path).startswith(str(web_dir_resolved)) and not str(resolved_path).startswith(str(output_dir_resolved)):
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

        if not api_key:
            self._send_json({"success": False, "error": "API key is required"}, 400)
            return

        llm_client = LLMClient(provider=provider, api_key=api_key)
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

        if not target_path:
            self._send_json({"success": False, "error": "Repository path or URL is required."}, 400)
            return

        # Setup custom environment variables temporarily if keys provided
        old_keys = {}
        if api_key:
            env_map = {
                "gemini": "GEMINI_API_KEY",
                "openai": "OPENAI_API_KEY",
                "claude": "ANTHROPIC_API_KEY"
            }
            env_var = env_map.get(provider.lower())
            if env_var:
                old_keys[env_var] = os.environ.get(env_var)
                os.environ[env_var] = api_key

        reader = None
        try:
            reader = ReaderAgent(target_path)
            reader.setup()
            scan_results = reader.scan_codebase()

            # Instantiate LLM client and analyze
            llm_client = LLMClient(provider=provider, model=model, api_key=api_key, base_url=base_url)
            analyzer = AnalyzerAgent(llm_client)
            analysis = analyzer.analyze(scan_results)

            # Generate completeness score
            score = self._calculate_readme_score(analysis, scan_results)

            self._send_json({
                "success": True,
                "score": score,
                "scan": scan_results,
                "analysis": analysis
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
            # Restore environment keys
            for k, val in old_keys.items():
                if val is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = val

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

        if not scan_results or not analysis:
            self._send_json({"success": False, "error": "Analysis context is missing."}, 400)
            return

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

        # Setup environment variables temporarily if keys provided
        old_keys = {}
        if api_key:
            env_map = {
                "gemini": "GEMINI_API_KEY",
                "openai": "OPENAI_API_KEY",
                "claude": "ANTHROPIC_API_KEY"
            }
            env_var = env_map.get(provider.lower())
            if env_var:
                old_keys[env_var] = os.environ.get(env_var)
                os.environ[env_var] = api_key

        try:
            llm_client = LLMClient(provider=provider, model=model, api_key=api_key, base_url=base_url)
            writer = WriterAgent(llm_client)
            
            # Determine output_dir
            target_path = scan_results.get("path", ".")
            output_dir = Path(target_path)
            if not output_dir.exists() or "readme_forge_clone_" in output_dir.name:
                output_dir = Path("./readme_forge_output")
                output_dir.mkdir(exist_ok=True)

            readme_md = writer.generate_readme(
                scan_results=scan_results,
                analysis=analysis,
                interactive_answers=custom_answers,
                style=readme_style,
                output_dir=output_dir,
                target_path_or_url=target_path,
                lang=lang
            )
            showroom_html = writer.generate_showroom_html(readme_md, analysis)

            self._send_json({
                "success": True,
                "readme": readme_md,
                "showroom": showroom_html
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
            else:
                self._send_json({
                    "success": False,
                    "error_type": "generation_error",
                    "error": error_msg,
                    "hint": "An unexpected error occurred during README generation."
                }, 500)
        finally:
            # Restore environment keys
            for k, val in old_keys.items():
                if val is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = val

    def _send_json(self, data, status_code=200):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(data, indent=2).encode('utf-8'))

    def _calculate_readme_score(self, analysis, scan_results):
        """Calculates a visual completeness rating out of 100 based on structural analyzer results."""
        existing_readme = scan_results.get("existing_readme", "").strip()
        if not existing_readme:
            return 10  # Very poor default if README is empty

        score = 100
        improvements = analysis.get("improvements", [])
        
        # Deduct score based on issues
        # Critical issues (Mermaid flow diagram missing, no installation instructions) deduct more.
        for imp in improvements:
            imp_type = imp.get("type", "General").lower()
            if "structure" in imp_type:
                score -= 15
            elif "examples" in imp_type:
                score -= 15
            elif "configuration" in imp_type:
                score -= 10
            else:
                score -= 5
                
        # Limit minimum score
        return max(score, 15)


import urllib.parse

def run_server(port=8080):
    # Ensure web folder exists
    Path(project_root / "web").mkdir(exist_ok=True)
    
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
