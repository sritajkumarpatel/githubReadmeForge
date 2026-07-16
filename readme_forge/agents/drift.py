"""Documentation Drift Detector agent to discover undocumented repository changes."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class DriftDetector:
    """Compares the current codebase state with the active README.md to check for undocumented code changes."""

    def __init__(self, target_path: str):
        self.target_path = Path(target_path).resolve()
        self.readme_path = self.target_path / "README.md"

    def detect(self, scan_results: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Return a list of undocumented features, endpoints, configs, or dependencies."""
        if not self.readme_path.exists():
            return [{
                "type": "general",
                "item": "README.md",
                "message": "README.md does not exist in target directory."
            }]

        readme_content = self.readme_path.read_text(encoding="utf-8").lower()
        drifts = []

        # 1. Check Configuration variables
        for cv in analysis.get("config_variables", []):
            name = cv.get("name", "").strip()
            if name and name.lower() not in readme_content:
                drifts.append({
                    "type": "configuration",
                    "item": name,
                    "message": f"Configuration variable '{name}' is defined in code but missing from README."
                })

        # 2. Check CLI commands
        for cmd in analysis.get("cli_commands", []):
            command = cmd.get("command", "").strip()
            if command and command.lower() not in readme_content:
                drifts.append({
                    "type": "cli",
                    "item": command,
                    "message": f"CLI command '{command}' is supported by arguments parser but missing from README."
                })

        # 3. Check API endpoints
        for ep in analysis.get("api_endpoints", []):
            path = ep.get("path", "").strip()
            if path and path.lower() not in readme_content:
                drifts.append({
                    "type": "api",
                    "item": path,
                    "message": f"API route '{path}' is defined in source endpoints but missing from README."
                })

        # 4. Check Tech/Dependencies
        for tech in analysis.get("tech_stack", []):
            if isinstance(tech, str) and tech.strip():
                name = tech.strip()
                if name.lower() not in readme_content:
                    drifts.append({
                        "type": "dependency",
                        "item": name,
                        "message": f"Dependency/tech component '{name}' is used but not mentioned in README."
                    })

        return drifts
