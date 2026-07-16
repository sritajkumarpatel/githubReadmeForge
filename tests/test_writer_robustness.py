"""Tests to verify WriterAgent safety coercion methods function properly and protect against schema deviations."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from readme_forge.agents.writer import WriterAgent


def test_writer_coerce_list_primitives():
    """_coerce_list must convert flat elements and primitive inputs to simple string lists."""
    agent = WriterAgent(None)

    assert agent._coerce_list(["hello", "world"]) == ["hello", "world"]
    assert agent._coerce_list("hello") == ["hello"]
    assert agent._coerce_list(None) == []


def test_writer_coerce_list_dictionaries():
    """_coerce_list must gracefully extract string names/paths/files from dict elements."""
    agent = WriterAgent(None)

    input_data = [
        {"name": "Python"},
        {"path": "src/main.py"},
        {"file": "cli.py"},
        {"other": "custom"},
    ]
    expected = ["Python", "src/main.py", "cli.py", "custom"]
    assert agent._coerce_list(input_data) == expected


def test_writer_safe_get_dict():
    """_safe_get_dict must return original dict, or map a primitive to standard keys, or return empty dict."""
    agent = WriterAgent(None)

    # original dict is preserved
    original = {"name": "test"}
    assert agent._safe_get_dict(original) == original

    # string element is mapped to sensible defaults
    string_item = "argparse"
    res = agent._safe_get_dict(string_item)
    assert isinstance(res, dict)
    assert res["name"] == "argparse"
    assert res["title"] == "argparse"

    # other primitives return empty dict
    assert agent._safe_get_dict(None) == {}
