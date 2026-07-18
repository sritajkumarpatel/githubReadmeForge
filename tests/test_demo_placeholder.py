"""Tests for the demo placeholder section in the WriterAgent."""

from readme_forge.agents.writer import WriterAgent
from readme_forge.llm import LLMClient


def _make_writer():
    return WriterAgent(LLMClient(provider="gemini", api_key="test"))


def test_demo_placeholder_included_for_visual_project_without_assets():
    writer = _make_writer()
    analysis = {
        "has_visual_interface": True,
        "recommended_style": "narrative",
        "hero_assets": [],
        "ui_assets": [],
    }
    assert writer._should_include_demo_placeholder(analysis) is True


def test_demo_placeholder_skipped_when_hero_assets_exist():
    writer = _make_writer()
    analysis = {
        "has_visual_interface": True,
        "recommended_style": "narrative",
        "hero_assets": [{"path": "assets/screenshot.png"}],
        "ui_assets": [],
    }
    assert writer._should_include_demo_placeholder(analysis) is False


def test_demo_placeholder_skipped_when_ui_assets_exist():
    writer = _make_writer()
    analysis = {
        "has_visual_interface": True,
        "recommended_style": "narrative",
        "hero_assets": [],
        "ui_assets": ["docs/screenshot.png"],
    }
    assert writer._should_include_demo_placeholder(analysis) is False


def test_demo_placeholder_skipped_for_non_visual_project():
    writer = _make_writer()
    analysis = {
        "has_visual_interface": False,
        "recommended_style": "reference",
        "hero_assets": [],
        "ui_assets": [],
    }
    assert writer._should_include_demo_placeholder(analysis) is False


def test_demo_placeholder_included_for_showcase_style():
    writer = _make_writer()
    analysis = {
        "has_visual_interface": False,
        "recommended_style": "showcase",
        "hero_assets": [],
        "ui_assets": [],
    }
    assert writer._should_include_demo_placeholder(analysis) is True


def test_demo_placeholder_included_for_demo_style():
    writer = _make_writer()
    analysis = {
        "has_visual_interface": False,
        "recommended_style": "demo",
        "hero_assets": [],
        "ui_assets": [],
    }
    assert writer._should_include_demo_placeholder(analysis) is True


def test_demo_placeholder_skipped_for_tutorial_style():
    writer = _make_writer()
    analysis = {
        "has_visual_interface": False,
        "recommended_style": "tutorial",
        "hero_assets": [],
        "ui_assets": [],
    }
    assert writer._should_include_demo_placeholder(analysis) is False


def test_demo_placeholder_skipped_for_minimal_style():
    writer = _make_writer()
    analysis = {
        "has_visual_interface": False,
        "recommended_style": "minimal",
        "hero_assets": [],
        "ui_assets": [],
    }
    assert writer._should_include_demo_placeholder(analysis) is False


def test_demo_placeholder_handles_empty_analysis():
    writer = _make_writer()
    assert writer._should_include_demo_placeholder({}) is False
    assert writer._should_include_demo_placeholder(None) is False


def test_demo_placeholder_text_is_friendly_and_actionable():
    writer = _make_writer()
    text = writer._get_demo_placeholder_section()

    # Verify the placeholder contains the key friendly elements
    assert "Check Out the Demo" in text
    assert "coming soon" in text.lower()
    assert "thank you" in text.lower()
    # Verify it includes actionable instructions
    assert "How to contribute" in text or "How to" in text
    # Verify it gives clear code examples for what to replace it with
    assert "![Demo" in text or "Watch the demo" in text


def test_demo_placeholder_does_not_contain_unverified_assets():
    """Make sure the placeholder doesn't accidentally claim real assets exist."""
    writer = _make_writer()
    text = writer._get_demo_placeholder_section()
    # No real file references that might not exist
    assert "https://example.com" not in text
    # It uses illustrative paths that are clearly examples
    assert "your-video-link-here" in text or "your-" in text
