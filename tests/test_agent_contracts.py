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
