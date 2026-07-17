"""Documentation Drift Detector agent to discover undocumented repository changes."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any


class DriftDetector:
    """Compares the current codebase state with the active README to check for undocumented
    code changes.

    Two modes of operation:
      1. detect(scan_results, analysis) — reads README from disk (works for local repos).
      2. detect_from_content(readme_content, scan_results, analysis) — accepts README text
         directly, which is required for remote/temp repos where the clone is already cleaned up.
    """

    def __init__(self, target_path: str):
        self.target_path = Path(target_path).resolve()
        self.readme_path = self.target_path / "README.md"

    # ── Public API ──────────────────────────────────────────────────────────

    def detect(self, scan_results: dict[str, Any], analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Detect drift by reading the README from disk (local repos only).

        For remote repos the clone is cleaned up before this is called — use
        detect_from_content() or pass the existing_readme from scan_results instead.
        """
        # Prefer the already-read content from scan_results (avoids disk read after cleanup).
        existing_readme = scan_results.get("existing_readme", "").strip() if scan_results else ""

        if existing_readme:
            return self._run_checks(existing_readme, analysis)

        # Fallback: try reading from disk (local repos where path is still valid).
        if not self.readme_path.exists():
            return [{
                "type": "general",
                "item": "README.md",
                "message": "README.md does not exist in target directory.",
            }]

        try:
            readme_content = self.readme_path.read_text(encoding="utf-8")
        except OSError as exc:
            return [{
                "type": "general",
                "item": "README.md",
                "message": f"Could not read README.md: {exc}",
            }]

        return self._run_checks(readme_content, analysis)

    def detect_from_content(
        self,
        readme_content: str,
        scan_results: dict[str, Any],
        analysis: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Detect drift from an already-loaded README string.

        Use this path for remote repositories where the temp clone has been deleted.
        """
        if not readme_content or not readme_content.strip():
            return [{
                "type": "general",
                "item": "README.md",
                "message": "README.md does not exist or is empty.",
            }]
        return self._run_checks(readme_content, analysis)

    # ── Internal helpers ────────────────────────────────────────────────────

    def _run_checks(self, readme_content: str, analysis: dict[str, Any]) -> list[dict[str, Any]]:
        """Core drift detection logic shared by both public methods."""
        readme_lower = readme_content.lower()
        drifts: list[dict[str, Any]] = []

        # 1. Configuration variables
        for cv in analysis.get("config_variables", []):
            name = cv.get("name", "").strip() if isinstance(cv, dict) else ""
            if name and name.lower() not in readme_lower:
                drifts.append({
                    "type": "configuration",
                    "item": name,
                    "message": (
                        f"Configuration variable '{name}' is defined in code "
                        "but missing from README."
                    ),
                })

        # 2. CLI commands — match the core command token, not the full flag string
        for cmd in analysis.get("cli_commands", []):
            command = cmd.get("command", "").strip() if isinstance(cmd, dict) else ""
            if not command:
                continue
            # Extract the binary/script name only (first word) for the match
            core_token = command.split()[0].lstrip("-").lower()
            if len(core_token) > 2 and core_token not in readme_lower:
                drifts.append({
                    "type": "cli",
                    "item": command,
                    "message": (
                        f"CLI command '{command}' is supported by the argument parser "
                        "but missing from README."
                    ),
                })

        # 3. API endpoints — match path segments, not the full path string
        for ep in analysis.get("api_endpoints", []):
            path = ep.get("path", "").strip() if isinstance(ep, dict) else ""
            if path and path.lower() not in readme_lower:
                drifts.append({
                    "type": "api",
                    "item": path,
                    "message": (
                        f"API route '{path}' is defined in source endpoints "
                        "but missing from README."
                    ),
                })

        # 4. Tech stack — use normalised matching to reduce false positives
        for tech in analysis.get("tech_stack", []):
            if not isinstance(tech, str) or not tech.strip():
                continue
            name = tech.strip()
            if not self._tech_in_readme(name, readme_lower):
                drifts.append({
                    "type": "dependency",
                    "item": name,
                    "message": (
                        f"Technology '{name}' is used in the project "
                        "but not mentioned in README."
                    ),
                })

        return drifts

    @staticmethod
    def _tech_in_readme(tech: str, readme_lower: str) -> bool:
        """Return True if the technology name is reasonably present in the README.

        Uses a tiered strategy to avoid false positives from multi-word or versioned names:
          1. Exact substring match (e.g. "fastapi" in readme).
          2. First significant word match (e.g. "Rich" from "Rich CLI").
          3. Acronym / abbreviation: last parenthesised token (e.g. "JS" from "JavaScript (JS)").
        """
        tech_lower = tech.lower().strip()

        # Exact match
        if tech_lower in readme_lower:
            return True

        # First significant word (skip very short tokens like 'a', 'by', 'v2')
        words = re.split(r"[\s\-_/]+", tech_lower)
        first_word = next((w for w in words if len(w) > 3), "")
        if first_word and first_word in readme_lower:
            return True

        # Last significant word (handles "Python 3.10" → "3.10" excluded, "Python" matched above)
        last_word = next((w for w in reversed(words) if len(w) > 3), "")
        if last_word and last_word != first_word and last_word in readme_lower:
            return True

        return False
