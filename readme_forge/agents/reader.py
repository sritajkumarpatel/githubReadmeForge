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
                subprocess.run(
                    ["git", "clone", "--depth", "1", target, temp_dir],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self.local_path = temp_dir
                self.is_temp = True
                print("[Reader] Clone successful.")
            except Exception as e:
                # Clean up and raise
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
        """Scans the codebase, extracting project tree structure and key config/source file contents."""
        if not self.local_path:
            raise RuntimeError("ReaderAgent not set up. Call setup() first.")
            
        tree_str = self._generate_tree(self.local_path)
        configs = self._read_config_files(self.local_path)
        existing_readme = self._read_existing_readme(self.local_path)
        code_context = self._read_primary_source_files(self.local_path)

        return {
            "path": self.local_path,
            "tree": tree_str,
            "configs": configs,
            "existing_readme": existing_readme,
            "code_context": code_context
        }

    def _generate_tree(self, path, max_depth=3):
        """Generates a text representation of the directory tree, ignoring build/dependencies folders."""
        ignored_dirs = {
            ".git", "node_modules", "venv", ".venv", "env", "__pycache__", 
            "build", "dist", ".pytest_cache", ".eggs", "*.egg-info", "bin", 
            "obj", "target", "vendor"
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
        """Reads project configuration files (e.g. package.json, requirements.txt, Cargo.toml)."""
        config_files = [
            "package.json", "requirements.txt", "setup.py", "pyproject.toml",
            "Cargo.toml", "go.mod", "Gemfile", "composer.json", "build.gradle",
            "pom.xml", "Makefile", "CMakeLists.txt", "DockerFile", "docker-compose.yml"
        ]
        
        configs = {}
        for f_name in config_files:
            file_path = Path(path) / f_name
            if file_path.exists() and file_path.is_file():
                try:
                    # Read at most 150 lines/5000 characters to prevent overflow
                    content = file_path.read_text(errors="ignore")
                    configs[f_name] = content[:5000]
                except Exception as e:
                    configs[f_name] = f"Error reading: {e}"
        return configs

    def _read_existing_readme(self, path):
        """Attempts to read the current README file."""
        readme_names = ["README.md", "readme.md", "README", "README.txt"]
        for f_name in readme_names:
            file_path = Path(path) / f_name
            if file_path.exists() and file_path.is_file():
                try:
                    return file_path.read_text(errors="ignore")[:8000]
                except Exception:
                    pass
        return ""

    def _read_primary_source_files(self, path, max_files=6):
        """Reads core entrypoint source files to understand the coding interface and entry files."""
        # Common source extensions and potential entry points
        source_extensions = {".py", ".js", ".ts", ".go", ".rs", ".java", ".cpp", ".cs"}
        entry_patterns = {"main", "app", "index", "cli", "run", "server"}
        
        scanned_files = {}
        path_obj = Path(path)
        
        file_candidates = []
        for root, dirs, files in os.walk(path_obj):
            # Ignore dependency paths
            dirs[:] = [d for d in dirs if d not in {".git", "node_modules", "venv", "__pycache__", "build", "dist", "vendor"}]
            
            for file in files:
                p = Path(root) / file
                if p.suffix in source_extensions:
                    score = 0
                    # Rank candidate by potential entrypoint name
                    if any(pat in p.stem.lower() for pat in entry_patterns):
                        score += 10
                    # Rank higher if close to the root
                    score -= len(p.relative_to(path_obj).parts)
                    file_candidates.append((score, p))
                    
        # Sort candidates and take top ones
        file_candidates.sort(key=lambda x: x[0], reverse=True)
        
        for _, p in file_candidates[:max_files]:
            try:
                rel_path = str(p.relative_to(path_obj))
                content = p.read_text(errors="ignore")
                # Take first 100 lines/3000 chars of each file
                scanned_files[rel_path] = content[:3000]
            except Exception:
                pass
                
        return scanned_files
