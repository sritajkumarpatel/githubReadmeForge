"""Tests for AnalyzerAgent — verifies fallback JSON is valid on bad LLM output."""
import sys
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from readme_forge.agents.analyzer import AnalyzerAgent

# Minimal scan_results stub
MINIMAL_SCAN = {
    "tree": ".\n└── main.py",
    "configs": {},
    "code_context": {"main.py": "print('hello')"},
    "existing_readme": "",
    "test_signals": {"has_tests": False, "framework": "unknown", "file_count": 0, "sample_test": ""},
    "version_info": {"version": "0.1.0", "changelog_snippet": ""},
    "external_api_calls": [],
    "narrative_hints": [],
    "path": ".",
}


def _make_analyzer(response_text: str) -> AnalyzerAgent:
    """Build an AnalyzerAgent whose LLM always returns response_text."""
    mock_llm = MagicMock()
    mock_llm.provider = "mock"
    mock_llm.generate.return_value = response_text
    return AnalyzerAgent(mock_llm)


def test_valid_json_response_is_parsed():
    """When the LLM returns valid JSON, analyze() should return it parsed."""
    payload = {
        "project_name": "TestProject",
        "project_persona": "A test project",
        "tech_stack": ["Python"],
        "project_type": "cli",
        "maturity": "development",
        "features": [],
        "improvements": [],
        "architecture_layers": [],
        "data_models": [],
        "installation_commands": [],
        "external_services": [],
        "test_coverage": {"framework": "pytest", "has_tests": False, "coverage_pct": None},
        "connections": [],
    }
    analyzer = _make_analyzer(json.dumps(payload))
    result = analyzer.analyze(MINIMAL_SCAN)

    assert result["project_name"] == "TestProject"
    assert result["tech_stack"] == ["Python"]


def test_json_wrapped_in_fences_is_parsed():
    """LLMs commonly wrap JSON in ```json ... ``` — analyzer must strip it."""
    payload = {"project_name": "Wrapped", "tech_stack": ["Go"], "improvements": []}
    fence_response = f"```json\n{json.dumps(payload)}\n```"
    analyzer = _make_analyzer(fence_response)
    result = analyzer.analyze(MINIMAL_SCAN)

    assert result["project_name"] == "Wrapped"


def test_completely_broken_response_returns_fallback():
    """When the LLM returns garbage, analyze() must return the safe fallback dict."""
    analyzer = _make_analyzer("I am an AI and I cannot do that. 🤖")
    result = analyzer.analyze(MINIMAL_SCAN)

    # Must always have these keys — agents downstream depend on them
    required = ["project_name", "tech_stack", "improvements", "architecture_layers",
                "data_models", "installation_commands", "external_services", "test_coverage"]
    missing = [k for k in required if k not in result]
    assert not missing, f"Fallback result missing keys: {missing}"


def test_partial_json_returns_fallback():
    """Truncated JSON (common with token limits) must return fallback, not raise."""
    truncated = '{"project_name": "Half", "tech_stack": ["Python"'  # no closing brackets
    analyzer = _make_analyzer(truncated)
    result = analyzer.analyze(MINIMAL_SCAN)

    # Should not raise, and should have fallback fields
    assert "improvements" in result


def test_fallback_tech_stack_is_list():
    """Fallback dict must always have tech_stack as a list, even when empty."""
    analyzer = _make_analyzer("")
    result = analyzer.analyze(MINIMAL_SCAN)
    assert isinstance(result.get("tech_stack", []), list)
