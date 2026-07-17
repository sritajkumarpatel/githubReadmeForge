import os
import re
import json
import shutil
import subprocess
import tempfile
from pathlib import Path


class ReaderAgent:
    def __init__(self, target_path_or_url):
        self.target_path_or_url = target_path_or_url
        self.local_path = None
        self.is_temp = False

    def setup(self):
        """Prepare the codebase. Clones if target is a URL, else uses the local path."""
        target = self.target_path_or_url.strip()

        if target.startswith("http://") or target.startswith("https://") or target.endswith(".git"):
            print(f"[Reader] Cloning repository from {target}...")
            temp_dir = tempfile.mkdtemp(prefix="readme_forge_clone_")
            try:
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", target, temp_dir],
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    error_msg = result.stderr.strip() if result.stderr else "Unknown git error"
                    if "Authentication failed" in error_msg or "permission denied" in error_msg.lower():
                        raise RuntimeError("Authentication failed: Invalid or missing GitHub credentials for private repository.")
                    elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                        raise RuntimeError("Repository not found: The specified GitHub URL does not exist or is not accessible.")
                    elif "rate limit" in error_msg.lower():
                        raise RuntimeError("GitHub rate limit exceeded. Please try again later or provide a personal access token.")
                    else:
                        raise RuntimeError(f"Git clone failed: {error_msg}")

                cloned_path = Path(temp_dir)
                files = list(cloned_path.rglob("*"))
                if len(files) < 3:
                    raise RuntimeError("Clone completed but repository appears empty or invalid.")

                self.local_path = temp_dir
                self.is_temp = True
                print("[Reader] Clone successful.")
            except RuntimeError:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise
            except Exception as e:
                shutil.rmtree(temp_dir, ignore_errors=True)
                raise RuntimeError(f"Failed to clone repository: {e}")
        else:
            path = Path(target).resolve()
            if not path.exists():
                raise FileNotFoundError(f"Local path does not exist: {target}")
            self.local_path = str(path)
            print(f"[Reader] Using local directory: {self.local_path}")

    def cleanup(self):
        """Clean up cloned directories if they are temporary."""
        if self.is_temp and self.local_path and os.path.exists(self.local_path):
            print("[Reader] Cleaning up temporary clone directory...")
            shutil.rmtree(self.local_path, ignore_errors=True)

    def scan_codebase(self):
        """Scans the codebase, extracting project tree, config files, source code, narrative hints,
        test signals, version info, and external API calls for richer analysis."""
        if not self.local_path:
            raise RuntimeError("ReaderAgent not set up. Call setup() first.")

        tree_str = self._generate_tree(self.local_path)
        configs = self._read_config_files(self.local_path)
        existing_readme = self._read_existing_readme(self.local_path)
        code_context = self._read_primary_source_files(self.local_path)
        narrative_hints = self._extract_narrative_hints(self.local_path)
        test_signals = self._extract_test_signals(self.local_path)
        version_info = self._extract_version_and_changelog(self.local_path)
        external_api_calls = self._infer_external_apis(self.local_path)

        return {
            "path": self.local_path,
            "tree": tree_str,
            "configs": configs,
            "existing_readme": existing_readme,
            "code_context": code_context,
            "narrative_hints": narrative_hints,
            "test_signals": test_signals,
            "version_info": version_info,
            "external_api_calls": external_api_calls,
        }

    def _generate_tree(self, path, max_depth=4):
        """Generates a text representation of the directory tree, ignoring build/dependency folders."""
        ignored_dirs = {
            ".git", "node_modules", "venv", ".venv", "env", "__pycache__",
            "build", "dist", ".pytest_cache", ".eggs", "*.egg-info", "bin",
            "obj", "target", "vendor", ".next", ".nuxt", "coverage",
            ".tox", ".mypy_cache",
        }

        lines = []
        path_obj = Path(path)

        def walk(current_dir, prefix="", depth=0):
            if depth > max_depth:
                lines.append(f"{prefix}...")
                return

            try:
                items = sorted(list(current_dir.iterdir()), key=lambda x: (not x.is_dir(), x.name))
            except PermissionError:
                return

            for i, item in enumerate(items):
                if item.name in ignored_dirs or any(item.match(pat) for pat in ignored_dirs):
                    continue

                is_last = i == len(items) - 1
                connector = "└── " if is_last else "├── "
                lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")

                if item.is_dir():
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    walk(item, new_prefix, depth + 1)

        lines.append(path_obj.name + "/")
        walk(path_obj)
        return "\n".join(lines)

    def _read_config_files(self, path):
        """Reads project configuration files including env templates, Docker, CI/CD, and test configs."""
        explicit_files = [
            # Package managers
            "package.json", "requirements.txt", "setup.py", "pyproject.toml",
            "Cargo.toml", "go.mod", "Gemfile", "composer.json", "build.gradle",
            "pom.xml", "setup.cfg",
            # Build/deploy
            "Makefile", "CMakeLists.txt", "Dockerfile", "docker-compose.yml",
            "docker-compose.yaml", "Dockerfile.dev",
            # Environment
            ".env.example", ".env.sample", ".env.template",
            # Frontend config
            "tsconfig.json", "webpack.config.js", "vite.config.js",
            "next.config.js", "tailwind.config.js",
            # Test config
            "jest.config.js", "jest.config.ts", "pytest.ini", "vitest.config.ts",
            ".eslintrc", ".eslintrc.js", ".eslintrc.json",
            # CI/CD (explicit paths)
            ".github/workflows/ci.yml", ".github/workflows/ci.yaml",
            ".github/workflows/main.yml", ".github/workflows/deploy.yml",
            ".gitlab-ci.yml",
        ]

        configs = {}
        path_obj = Path(path)

        # Read all explicitly named files
        for f_name in explicit_files:
            file_path = path_obj / f_name
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(errors="ignore")
                    configs[f_name] = content[:6000]
                except Exception as e:
                    configs[f_name] = f"Error reading: {e}"

        # Glob scan for any remaining GitHub Actions workflows not in explicit list
        workflows_dir = path_obj / ".github" / "workflows"
        if workflows_dir.is_dir():
            for wf_file in workflows_dir.glob("*.yml"):
                key = f".github/workflows/{wf_file.name}"
                if key not in configs:
                    try:
                        configs[key] = wf_file.read_text(errors="ignore")[:4000]
                    except Exception:
                        pass
            for wf_file in workflows_dir.glob("*.yaml"):
                key = f".github/workflows/{wf_file.name}"
                if key not in configs:
                    try:
                        configs[key] = wf_file.read_text(errors="ignore")[:4000]
                    except Exception:
                        pass

        return configs

    def _read_existing_readme(self, path):
        """Attempts to read the current README file."""
        readme_names = ["README.md", "readme.md", "README", "README.txt", "README.rst"]
        for f_name in readme_names:
            file_path = Path(path) / f_name
            if file_path.exists() and file_path.is_file():
                try:
                    return file_path.read_text(errors="ignore")[:10000]
                except Exception:
                    pass
        return ""

    def _read_primary_source_files(self, path, max_files=20):
        """Reads core source files with intelligent prioritization for deeper context extraction."""
        source_extensions = {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs",
            ".java", ".cpp", ".cs", ".rb", ".swift", ".kt",
        }

        entry_patterns = {"main", "app", "index", "cli", "run", "server", "api"}
        architecture_patterns = {
            "agent", "route", "handler", "controller", "middleware",
            "service", "model", "config", "orchestrat", "pipeline",
            "workflow", "manager", "store", "provider", "factory",
        }

        scanned_files = {}
        path_obj = Path(path)

        ignored_dirs = {
            ".git", "node_modules", "venv", ".venv", "__pycache__",
            "build", "dist", "vendor", "coverage", ".next",
        }

        file_candidates = []
        for root, dirs, files in os.walk(path_obj):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]

            for file in files:
                p = Path(root) / file
                if p.suffix not in source_extensions:
                    continue

                score = 0
                name_lower = p.stem.lower()

                if any(pat in name_lower for pat in entry_patterns):
                    score += 10
                if any(pat in name_lower for pat in architecture_patterns):
                    score += 8

                # Boost __init__.py files that have module docstrings
                if name_lower == "__init__":
                    try:
                        first_bytes = p.read_text(errors="ignore")[:300]
                        if '"""' in first_bytes or "'''" in first_bytes:
                            score += 5
                        else:
                            score -= 2  # empty __init__ not useful
                    except Exception:
                        pass

                # Boost files with docstrings/comments at the top
                try:
                    first_line = p.read_text(errors="ignore")[:200]
                    if '"""' in first_line or "'''" in first_line or "/**" in first_line:
                        score += 3
                except Exception:
                    pass

                # Penalise depth from root
                score -= len(p.relative_to(path_obj).parts)
                file_candidates.append((score, p))

        file_candidates.sort(key=lambda x: x[0], reverse=True)

        total_chars = 0
        char_budget = 50_000
        for _, p in file_candidates:
            try:
                rel_path = str(p.relative_to(path_obj))
                content = p.read_text(errors="ignore")
                content_to_use = content[:8000]
                
                if total_chars + len(content_to_use) <= char_budget:
                    scanned_files[rel_path] = content_to_use
                    total_chars += len(content_to_use)
                else:
                    rem = char_budget - total_chars
                    if rem > 1000:
                        scanned_files[rel_path] = content_to_use[:rem] + "\n\n[Content Truncated due to size constraints...]"
                    break
            except Exception:
                pass

        return scanned_files

    def _extract_narrative_hints(self, path):
        """Extracts module-level docstrings, comments, and description fields as narrative hints."""
        hints = []
        path_obj = Path(path)

        pkg_json = path_obj / "package.json"
        if pkg_json.exists():
            try:
                data = json.loads(pkg_json.read_text(errors="ignore"))
                if data.get("description"):
                    hints.append(f"package.json description: {data['description']}")
                if data.get("keywords"):
                    hints.append(f"package.json keywords: {', '.join(data['keywords'])}")
                if data.get("version"):
                    hints.append(f"package.json version: {data['version']}")
            except Exception:
                pass

        setup_py = path_obj / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text(errors="ignore")
                for line in content.splitlines():
                    if "description=" in line or "description =" in line:
                        hints.append(f"setup.py: {line.strip()}")
                        break
            except Exception:
                pass

        pyproject = path_obj / "pyproject.toml"
        if pyproject.exists():
            try:
                content = pyproject.read_text(errors="ignore")
                for line in content.splitlines():
                    if line.strip().startswith("description"):
                        hints.append(f"pyproject.toml: {line.strip()}")
                        break
            except Exception:
                pass

        for entry_name in [
            "main.py", "app.py", "index.py", "cli.py", "server.py",
            "src/index.ts", "src/main.ts",
        ]:
            entry_file = path_obj / entry_name
            if entry_file.exists():
                try:
                    content = entry_file.read_text(errors="ignore")[:500]
                    lines = content.splitlines()
                    for line in lines[:10]:
                        stripped = line.strip()
                        if stripped.startswith('"""') or stripped.startswith("'''"):
                            hints.append(f"{entry_name} docstring: {stripped}")
                        elif stripped.startswith("//") or stripped.startswith("#"):
                            if len(stripped) > 5:
                                hints.append(f"{entry_name} header: {stripped}")
                except Exception:
                    pass

        return hints

    def _extract_test_signals(self, path):
        """Detects testing framework, counts test files, and samples a test docstring."""
        path_obj = Path(path)
        test_dirs = ["tests", "test", "__tests__", "spec", "specs", "src/__tests__"]
        test_file_patterns = ["test_*.py", "*_test.py", "*.test.ts", "*.test.js",
                               "*.spec.ts", "*.spec.js", "*.test.tsx"]

        framework = "unknown"
        file_count = 0
        sample_test = ""

        # Detect framework from config files
        if (path_obj / "pytest.ini").exists() or (path_obj / "pyproject.toml").exists():
            try:
                content = (path_obj / "pyproject.toml").read_text(errors="ignore") if (path_obj / "pyproject.toml").exists() else ""
                if "pytest" in content or (path_obj / "pytest.ini").exists():
                    framework = "pytest"
            except Exception:
                framework = "pytest"

        if (path_obj / "jest.config.js").exists() or (path_obj / "jest.config.ts").exists():
            framework = "jest"
        if (path_obj / "vitest.config.ts").exists():
            framework = "vitest"

        # Count test files across test directories and root
        test_files_found = []
        for test_dir_name in test_dirs:
            test_dir = path_obj / test_dir_name
            if test_dir.is_dir():
                for root, dirs, files in os.walk(test_dir):
                    dirs[:] = [d for d in dirs if d not in {"__pycache__", "node_modules"}]
                    for f in files:
                        p = Path(root) / f
                        if any(p.match(pat) for pat in test_file_patterns) or \
                           p.suffix in {".py", ".ts", ".js", ".tsx", ".jsx"}:
                            test_files_found.append(p)

        # Also scan root for test files
        for pat in test_file_patterns:
            test_files_found.extend(path_obj.glob(pat))

        file_count = len(set(test_files_found))

        # Auto-detect framework from test file imports if still unknown
        if framework == "unknown" and test_files_found:
            try:
                sample_content = test_files_found[0].read_text(errors="ignore")[:500]
                if "import pytest" in sample_content or "from pytest" in sample_content:
                    framework = "pytest"
                elif "import unittest" in sample_content:
                    framework = "unittest"
                elif "describe(" in sample_content or "it(" in sample_content:
                    framework = "jest/mocha"
                elif "from vitest" in sample_content or "import { test }" in sample_content:
                    framework = "vitest"
            except Exception:
                pass

        # Get a sample docstring or first meaningful comment from first test file
        if test_files_found:
            try:
                content = test_files_found[0].read_text(errors="ignore")[:600]
                lines = content.splitlines()
                for line in lines[:15]:
                    stripped = line.strip()
                    if stripped.startswith('"""') or stripped.startswith("def test_"):
                        sample_test = stripped[:200]
                        break
            except Exception:
                pass

        return {
            "framework": framework,
            "file_count": file_count,
            "sample_test": sample_test,
            "has_tests": file_count > 0,
        }

    def _extract_version_and_changelog(self, path):
        """Extracts current version number and recent changelog entries."""
        path_obj = Path(path)
        version = ""
        changelog_snippet = ""

        # Try CHANGELOG.md / HISTORY.md first
        for changelog_name in ["CHANGELOG.md", "CHANGELOG", "HISTORY.md", "CHANGES.md"]:
            changelog_path = path_obj / changelog_name
            if changelog_path.exists():
                try:
                    content = changelog_path.read_text(errors="ignore")[:3000]
                    changelog_snippet = content
                    # Try to extract version from first heading
                    match = re.search(r"##\s*[\[\(]?v?([\d]+\.[\d]+\.[\d]+)", content)
                    if match:
                        version = match.group(1)
                    break
                except Exception:
                    pass

        # Fallback: package.json version
        if not version:
            pkg_json = path_obj / "package.json"
            if pkg_json.exists():
                try:
                    data = json.loads(pkg_json.read_text(errors="ignore"))
                    version = data.get("version", "")
                except Exception:
                    pass

        # Fallback: setup.py version=
        if not version:
            setup_py = path_obj / "setup.py"
            if setup_py.exists():
                try:
                    content = setup_py.read_text(errors="ignore")
                    match = re.search(r'version\s*=\s*["\']([^"\']+)["\']', content)
                    if match:
                        version = match.group(1)
                except Exception:
                    pass

        # Fallback: pyproject.toml version =
        if not version:
            pyproject = path_obj / "pyproject.toml"
            if pyproject.exists():
                try:
                    content = pyproject.read_text(errors="ignore")
                    match = re.search(r'^version\s*=\s*["\']([^"\']+)["\']', content, re.MULTILINE)
                    if match:
                        version = match.group(1)
                except Exception:
                    pass

        return {
            "version": version,
            "changelog_snippet": changelog_snippet[:1500] if changelog_snippet else "",
        }

    def _infer_external_apis(self, path):
        """Scans source files for outbound HTTP calls to infer external services used."""
        path_obj = Path(path)
        source_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rb"}

        ignored_dirs = {
            ".git", "node_modules", "venv", ".venv", "__pycache__",
            "build", "dist", "vendor", "coverage", ".next",
        }

        # Patterns that indicate outbound HTTP calls
        http_call_patterns = [
            r'requests\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'httpx\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'fetch\s*\(\s*["\']([^"\']+)["\']',
            r'axios\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
            r'urllib\.request\.urlopen\s*\(\s*["\']([^"\']+)["\']',
            r'http\.NewRequest\s*\(\s*["\'][A-Z]+["\'],\s*["\']([^"\']+)["\']',
        ]

        found_urls = set()

        for root, dirs, files in os.walk(path_obj):
            dirs[:] = [d for d in dirs if d not in ignored_dirs]
            for file in files:
                p = Path(root) / file
                if p.suffix not in source_extensions:
                    continue
                try:
                    content = p.read_text(errors="ignore")
                    for pattern in http_call_patterns:
                        matches = re.findall(pattern, content)
                        for m in matches:
                            # m may be a tuple (from groups) or string
                            url = m[-1] if isinstance(m, tuple) else m
                            if url.startswith("http"):
                                # Extract just the domain
                                domain_match = re.match(r"https?://([^/]+)", url)
                                if domain_match:
                                    found_urls.add(domain_match.group(1))
                except Exception:
                    pass

        # Also look for base URLs in env example files
        env_files = [".env.example", ".env.sample", ".env.template"]
        for env_name in env_files:
            env_path = path_obj / env_name
            if env_path.exists():
                try:
                    content = env_path.read_text(errors="ignore")
                    for line in content.splitlines():
                        url_match = re.search(r"https?://([a-zA-Z0-9\-\.]+\.[a-zA-Z]{2,})", line)
                        if url_match:
                            found_urls.add(url_match.group(1))
                except Exception:
                    pass

        return sorted(found_urls)
