"""Tests for the portable README visual asset generator."""

from readme_forge.visual_assets import VisualAssetGenerator, select_component_flow


def test_component_flow_keeps_a_single_short_critical_path():
    connections = [
        {"from": "Browser UI", "to": "API Server", "relationship": "submits repository"},
        {"from": "API Server", "to": "Reader Agent", "relationship": "scans files"},
        {"from": "Reader Agent", "to": "Analyzer Agent", "relationship": "provides evidence"},
        {"from": "Analyzer Agent", "to": "Writer Agent", "relationship": "plans documentation"},
        {"from": "Writer Agent", "to": "README.md", "relationship": "writes output"},
        {"from": "Analyzer Agent", "to": "Telemetry", "relationship": "emits metrics"},
    ]

    flow = select_component_flow(connections)

    assert len(flow) == 4
    assert flow[0]["from"] == "Browser UI"
    assert flow[-1]["to"] == "Writer Agent"
    assert all(edge["to"] != "Telemetry" for edge in flow)


def test_visual_generator_writes_portable_assets_and_references(tmp_path):
    analysis = {
        "project_name": "Forge",
        "project_persona": "A visual documentation workspace",
        "tech_stack": ["Python", "FastAPI", "Docker"],
        "connections": [
            {"from": "Dashboard", "to": "Analyzer", "relationship": "starts analysis"},
            {"from": "Analyzer", "to": "README", "relationship": "creates docs"},
        ],
    }

    generator = VisualAssetGenerator(tmp_path)
    assets = generator.generate(analysis)
    markdown = generator.markdown_intro(assets)

    assert (tmp_path / "assets/readme/brand-light.svg").exists()
    assert (tmp_path / "assets/readme/brand-dark.svg").exists()
    assert (tmp_path / "assets/readme/architecture.svg").exists()
    assert (tmp_path / "assets/readme/ATTRIBUTIONS.md").exists()
    assert "assets/readme/brand-light.svg" in markdown
    assert "cdn.simpleicons.org/python" in markdown
