"""githubReadmeForge — Multi-agent CLI & Web tool for AI-powered README generation."""

__version__ = "0.2.0"
__author__ = "githubReadmeForge Contributors"

import os
from pathlib import Path

def load_env_file():
    """Load local .env file key-value pairs into os.environ if it exists."""
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                if key:
                    os.environ.setdefault(key, val)
