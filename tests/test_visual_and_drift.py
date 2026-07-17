"""Unit tests for VisualAssetGenerator strategies and DriftDetector."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from readme_forge.visual_assets import VisualAssetGenerator
from readme_forge.agents.drift import DriftDetector


def test_visual_asset_generator_strategies(tmp_path):
    """VisualAssetGenerator must respect chosen strategy, generating correct files."""
    gen = VisualAssetGenerator(tmp_path)
    analysis = {
        "project_name": "Test project",
        "project_persona": "An API service",
        "connections": [{"from": "Client", "to": "Server", "relationship": "sends query"}],
        "tech_stack": ["Python", "FastAPI"]
    }

    # 1. API strategy
    assets_api = gen.generate(analysis, strategy="api")
    assert assets_api["brand_light"] == "assets/readme/brand-light.svg"
    assert (tmp_path / "assets" / "readme" / "brand-light.svg").exists()
    assert (tmp_path / "assets" / "readme" / "brand-dark.svg").exists()
    assert assets_api["architecture"] == ""
    assert len(assets_api["technology_icons"]) > 0

    # 2. Minimal strategy (no files generated)
    assets_min = gen.generate(analysis, strategy="minimal")
    assert assets_min["brand_light"] == ""
    assert assets_min["architecture"] == ""


def test_drift_detector(tmp_path):
    """DriftDetector must detect undocumented config keys, CLI commands, and endpoints."""
    readme_file = tmp_path / "README.md"
    readme_file.write_text("This is my python readme. E.g. run with Python and FastAPI.", encoding="utf-8")

    detector = DriftDetector(str(tmp_path))

    scan_results = {}
    analysis = {
        "config_variables": [
            {"name": "DATABASE_URL", "description": "Connection string"}
        ],
        "cli_commands": [
            {"command": "readme-forge --preview", "description": "Preview showroom"}
        ],
        "api_endpoints": [
            {"path": "/api/v1/generate", "description": "Generate documentation"}
        ],
        "tech_stack": ["Python", "FastAPI", "React"]
    }

    drifts = detector.detect(scan_results, analysis)
    types = [d["type"] for d in drifts]

    assert "configuration" in types
    assert "cli" in types
    assert "api" in types
    assert "dependency" in types  # React is missing from readme, but Python & FastAPI are present
