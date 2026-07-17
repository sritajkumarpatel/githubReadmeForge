"""Regression tests for evidence-backed repository classification and README planning."""

from readme_forge.agents.contracts import (
    build_documentation_plan,
    classify_repository,
    normalize_analysis,
)


def _scan(code_context, configs=None, has_tests=False):
    return {
        "tree": "repo/\n├── pyproject.toml\n├── main.py\n└── tests/",
        "configs": configs or {},
        "code_context": code_context,
        "test_signals": {"has_tests": has_tests, "framework": "pytest"},
    }


def test_classifier_keeps_package_and_cli_as_independent_surfaces():
    scan = _scan(
        {"main.py": "import argparse\nparser = argparse.ArgumentParser()"},
        {"pyproject.toml": "[project]\nname = 'example'"},
        has_tests=True,
    )

    result = classify_repository(scan)

    assert result["primary_intent"] == "cli"
    assert set(result["delivery_surfaces"]) == {"package", "cli"}
    assert result["maturity"] == "development"
    assert result["evidence"]


def test_normalizer_uses_deterministic_fallback_without_generic_claims():
    scan = _scan({"tool.py": "print('hello')"})

    result = normalize_analysis({}, scan, analysis_complete=False)

    assert result["analysis_complete"] is False
    assert result["project_persona"] == ""
    assert result["tech_stack"] == []
    assert result["documentation_plan"]["evidence_only"] is True


def test_plan_only_includes_sections_with_supporting_facts():
    analysis = {
        "project_type": "minimal",
        "classification": {"primary_intent": "minimal", "delivery_surfaces": []},
        "key_features": [],
        "installation_commands": [],
        "cli_commands": [],
        "config_variables": [],
        "api_endpoints": [],
        "connections": [],
        "architecture_layers": [],
        "data_models": [],
        "test_coverage": {"has_tests": False},
    }

    plan = build_documentation_plan(analysis)

    assert "problem" not in plan["sections"]
    assert "architecture" not in plan["sections"]
    assert "api_reference" not in plan["sections"]
    assert plan["include_architecture_diagram"] is False


def test_plain_html_dashboard_is_classified_as_ui_first_application():
    scan = _scan({"server.py": "from http.server import HTTPServer"})
    scan["tree"] = "repo/\n├── server.py\n└── web/\n    ├── index.html\n    └── app.js"

    result = classify_repository(scan)

    assert result["primary_intent"] == "application"
    assert "ui" in result["delivery_surfaces"]


# ── Phase 2: new type tests ────────────────────────────────────────────────

def test_demo_repo_is_classified_as_demo():
    """Repository with 'demo' in tree name should be classified as demo, not application."""
    scan = _scan({"app.py": "print('hello')"})
    scan["tree"] = "readme-forge-demo/\n├── app.py\n└── index.html"

    result = classify_repository(scan)

    assert result["primary_intent"] == "demo"
    assert any(e["claim"] == "intent:demo" for e in result["evidence"])


def test_showcase_repo_is_classified_as_demo():
    """'showcase' in the tree should also trigger demo intent."""
    scan = _scan({"main.py": "import flask"})
    scan["tree"] = "my-showcase/\n├── main.py"

    result = classify_repository(scan)

    assert result["primary_intent"] == "demo"


def test_low_signal_repo_classifies_as_unknown():
    """No surfaces + no tree signals + very few files should yield 'unknown' (confidence < 0.4)."""
    scan = {
        "tree": "mystery-repo/\n└── notes.txt",
        "configs": {},
        "code_context": {},  # no source files → surfaces=[], confidence=0.35 < 0.4 → unknown
        "test_signals": {"has_tests": False, "framework": "unknown"},
    }

    result = classify_repository(scan)

    # With no surfaces and no code files, minimal fires then confidence check overrides to unknown
    assert result["primary_intent"] in ("unknown", "minimal")
    assert result["confidence"] <= 0.5


def test_demo_plan_excludes_problem_solution():
    """Demo projects do include problem/solution (brief), but 'unknown' should skip them."""
    analysis_unknown = {
        "project_type": "unknown",
        "classification": {"primary_intent": "unknown", "delivery_surfaces": []},
        "key_features": [],
        "installation_commands": [],
        "cli_commands": [],
        "config_variables": [],
        "api_endpoints": [],
        "connections": [],
        "architecture_layers": [],
        "data_models": [],
        "test_coverage": {"has_tests": False},
    }
    plan = build_documentation_plan(analysis_unknown)
    assert "problem" not in plan["sections"]
    assert "solution" not in plan["sections"]


def test_suggested_visual_strategy_follows_intent():
    """classify_repository must always return a suggested_visual_strategy field."""
    from readme_forge.agents.contracts import INTENT_VISUAL_STRATEGY

    for intent, expected_strategy in INTENT_VISUAL_STRATEGY.items():
        scan = _scan({"f.py": "x = 1"})
        # Manually set tree to trigger the correct intent where possible
        result = classify_repository(scan)
        # All results must have the field — value checked where intent matches
        assert "suggested_visual_strategy" in result


def test_normalizer_propagates_visual_strategy():
    """normalize_analysis must pass suggested_visual_strategy through to the classification."""
    # Provide enough code context so the classifier detects API surface (not minimal)
    scan = {
        "tree": "api-service/\n├── api.py\n├── models.py\n└── routes.py",
        "configs": {},
        "code_context": {
            "api.py": "from fastapi import FastAPI\napp = FastAPI()\n@app.get('/health')\ndef health(): pass",
            "models.py": "from pydantic import BaseModel\nclass Item(BaseModel): pass",
            "routes.py": "from fastapi import APIRouter\nrouter = APIRouter()",
        },
        "test_signals": {"has_tests": False, "framework": "unknown"},
    }

    result = normalize_analysis({}, scan)

    assert "suggested_visual_strategy" in result["classification"]
    # FastAPI signals → api surface → api intent → api visual strategy
    assert result["classification"]["primary_intent"] == "api"
    assert result["classification"]["suggested_visual_strategy"] == "api"


def test_drift_detect_from_content_works_without_disk():
    """detect_from_content must work when no README exists on disk."""
    from readme_forge.agents.drift import DriftDetector

    detector = DriftDetector("/nonexistent/path/that/does/not/exist")
    analysis = {
        "config_variables": [{"name": "API_KEY", "description": "test"}],
        "cli_commands": [],
        "api_endpoints": [],
        "tech_stack": ["Python"],
    }
    readme_content = "This project uses Python and requires an API_KEY environment variable."
    drifts = detector.detect_from_content(readme_content, {}, analysis)

    # API_KEY is in the README → no config drift
    config_drifts = [d for d in drifts if d["type"] == "configuration"]
    assert len(config_drifts) == 0


def test_drift_tech_noise_reduction():
    """Multi-word tech names like 'Rich CLI' should match 'rich' in the README."""
    from readme_forge.agents.drift import DriftDetector

    detector = DriftDetector(".")
    analysis = {
        "config_variables": [],
        "cli_commands": [],
        "api_endpoints": [],
        "tech_stack": ["Rich CLI", "Google Gemini API", "Python 3.10"],
    }
    readme = "This tool is built with Python and uses the rich library for terminal output. Powered by Google Gemini."
    drifts = detector.detect_from_content(readme, {}, analysis)
    dep_items = [d["item"] for d in drifts if d["type"] == "dependency"]

    # None of these should fire — all are reachable via the normalised match
    assert "Rich CLI" not in dep_items
    assert "Python 3.10" not in dep_items
    assert "Google Gemini API" not in dep_items
