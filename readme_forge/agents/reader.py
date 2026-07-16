import os
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

        # Check if URL
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
                        raise RuntimeError(f"Authentication failed: Invalid or missing GitHub credentials for private repository.")
                    elif "not found" in error_msg.lower() or "does not exist" in error_msg.lower():
                        raise RuntimeError(f"Repository not found: The specified GitHub URL does not exist or is not accessible.")
                    elif "rate limit" in error_msg.lower():
                        raise RuntimeError(f"GitHub rate limit exceeded. Please try again later or provide a personal access token.")
                    else:
                        raise RuntimeError(f"Git clone failed: {error_msg}")

                # Validate cloned directory has content
                cloned_path = Path(temp_dir)
                files = list(cloned_path.rglob('*'))
                if len(files) < 3:
                    raise RuntimeError(f"Clone completed but repository appears empty or invalid.")

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
            # Local path
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
        """Scans the codebase, extracting project tree structure, config files, source code, and narrative hints."""
        if not self.local_path:
            raise RuntimeError("ReaderAgent not set up. Call setup() first.")
            
        tree_str = self._generate_tree(self.local_path)
        configs = self._read_config_files(self.local_path)
        existing_readme = self._read_existing_readme(self.local_path)
        code_context = self._read_primary_source_files(self.local_path)
        narrative_hints = self._extract_narrative_hints(self.local_path)

        return {
            "path": self.local_path,
            "tree": tree_str,
            "configs": configs,
            "existing_readme": existing_readme,
            "code_context": code_context,
            "narrative_hints": narrative_hints
        }

    def _generate_tree(self, path, max_depth=4):
        """Generates a text representation of the directory tree, ignoring build/dependencies folders."""
        ignored_dirs = {
            ".git", "node_modules", "venv", ".venv", "env", "__pycache__", 
            "build", "dist", ".pytest_cache", ".eggs", "*.egg-info", "bin", 
            "obj", "target", "vendor", ".next", ".nuxt", "coverage",
            ".tox", ".mypy_cache"
        }
        
        lines = []
        path_obj = Path(path)
        
        def walk(current_dir, prefix="", depth=0):
            if depth > max_depth:
                lines.append(f"{prefix}...")
                return
            
            # Sort files and folders
            try:
                items = sorted(list(current_dir.iterdir()), key=lambda x: (not x.is_dir(), x.name))
            except PermissionError:
                return
                
            for i, item in enumerate(items):
                # Check ignores
                if item.name in ignored_dirs or any(item.match(pat) for pat in ignored_dirs):
                    continue
                    
                is_last = (i == len(items) - 1)
                connector = "└── " if is_last else "├── "
                
                lines.append(f"{prefix}{connector}{item.name}{'/' if item.is_dir() else ''}")
                
                if item.is_dir():
                    new_prefix = prefix + ("    " if is_last else "│   ")
                    walk(item, new_prefix, depth + 1)

        lines.append(path_obj.name + "/")
        walk(path_obj)
        return "\n".join(lines)

    def _read_config_files(self, path):
        """Reads project configuration files including env templates and Docker configs."""
        config_files = [
            # Package managers
            "package.json", "requirements.txt", "setup.py", "pyproject.toml",
            "Cargo.toml", "go.mod", "Gemfile", "composer.json", "build.gradle",
            "pom.xml", "setup.cfg",
            # Build/deploy
            "Makefile", "CMakeLists.txt", "Dockerfile", "docker-compose.yml",
            "docker-compose.yaml",
            # Environment
            ".env.example", ".env.sample", ".env.template",
            # Config
            "tsconfig.json", "webpack.config.js", "vite.config.js",
            "next.config.js", "tailwind.config.js",
            # CI/CD
            ".github/workflows/ci.yml", ".github/workflows/ci.yaml",
            ".gitlab-ci.yml",
        ]
        
        configs = {}
        for f_name in config_files:
            file_path = Path(path) / f_name
            if file_path.exists() and file_path.is_file():
                try:
                    content = file_path.read_text(errors="ignore")
                    configs[f_name] = content[:6000]
                except Exception as e:
                    configs[f_name] = f"Error reading: {e}"
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

    def _read_primary_source_files(self, path, max_files=12):
        """Reads core source files with intelligent prioritization for deeper context extraction."""
        source_extensions = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".cpp", ".cs", ".rb"}
        
        # High-value filename patterns (scored higher)
        entry_patterns = {"main", "app", "index", "cli", "run", "server", "api"}
        architecture_patterns = {"agent", "route", "handler", "controller", "middleware", "service", "model", "config", "orchestrat"}
        
        scanned_files = {}
        path_obj = Path(path)
        
        file_candidates = []
        for root, dirs, files in os.walk(path_obj):
            # Ignore dependency paths
            dirs[:] = [d for d in dirs if d not in {
                ".git", "node_modules", "venv", ".venv", "__pycache__", 
                "build", "dist", "vendor", "coverage", ".next"
            }]
            
            for file in files:
                p = Path(root) / file
                if p.suffix in source_extensions:
                    score = 0
                    name_lower = p.stem.lower()
                    
                    # Rank candidate by potential entrypoint name
                    if any(pat in name_lower for pat in entry_patterns):
                        score += 10
                    
                    # Boost architecture-significant files
                    if any(pat in name_lower for pat in architecture_patterns):
                        score += 8
                    
                    # Boost files with docstrings/comments at the top (likely well-documented)
                    try:
                        first_line = p.read_text(errors="ignore")[:200]
                        if '"""' in first_line or "'''" in first_line or "/**" in first_line:
                            score += 3
                    except Exception:
                        pass
                    
                    # Rank higher if close to the root
                    score -= len(p.relative_to(path_obj).parts)
                    file_candidates.append((score, p))
                    
        # Sort candidates and take top ones
        file_candidates.sort(key=lambda x: x[0], reverse=True)
        
        for _, p in file_candidates[:max_files]:
            try:
                rel_path = str(p.relative_to(path_obj))
                content = p.read_text(errors="ignore")
                # Take first 5000 chars of each file for deeper context
                scanned_files[rel_path] = content[:5000]
            except Exception:
                pass
                
        return scanned_files

    def _extract_narrative_hints(self, path):
        """Extracts module-level docstrings, comments, and description fields as narrative hints for the analyzer."""
        hints = []
        path_obj = Path(path)
        
        # Extract description from package.json
        pkg_json = path_obj / "package.json"
        if pkg_json.exists():
            try:
                import json
                data = json.loads(pkg_json.read_text(errors="ignore"))
                if data.get("description"):
                    hints.append(f"package.json description: {data['description']}")
                if data.get("keywords"):
                    hints.append(f"package.json keywords: {', '.join(data['keywords'])}")
            except Exception:
                pass
        
        # Extract description from setup.py / pyproject.toml
        setup_py = path_obj / "setup.py"
        if setup_py.exists():
            try:
                content = setup_py.read_text(errors="ignore")
                # Look for description= in setup()
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
        
        # Extract top-level docstrings from main entry files
        for entry_name in ["main.py", "app.py", "index.py", "cli.py", "server.py", "src/index.ts", "src/main.ts"]:
            entry_file = path_obj / entry_name
            if entry_file.exists():
                try:
                    content = entry_file.read_text(errors="ignore")[:500]
                    # Check for module-level docstring
                    lines = content.splitlines()
                    for line in lines[:10]:
                        stripped = line.strip()
                        if stripped.startswith('"""') or stripped.startswith("'''"):
                            hints.append(f"{entry_name} docstring: {stripped}")
                        elif stripped.startswith("//") or stripped.startswith("#"):
                            if len(stripped) > 5:  # Skip trivial comments
                                hints.append(f"{entry_name} header: {stripped}")
                except Exception:
                    pass
        
        return hints
