"""Tests for ReaderAgent — verifies scan_codebase() contract."""
import sys
from pathlib import Path

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from readme_forge.agents.reader import ReaderAgent


REQUIRED_KEYS = [
    "tree",
    "configs",
    "code_context",
    "existing_readme",
    "test_signals",
    "version_info",
    "external_api_calls",
    "narrative_hints",
    "path",
]


def test_scan_returns_all_required_keys():
    """scan_codebase() must return every key the downstream agents depend on."""
    reader = ReaderAgent(".")
    reader.setup()
    result = reader.scan_codebase()

    missing = [k for k in REQUIRED_KEYS if k not in result]
    assert not missing, f"scan_codebase() missing keys: {missing}"


def test_scan_tree_is_nonempty_string():
    """The tree field must be a non-empty string (ASCII directory listing)."""
    reader = ReaderAgent(".")
    reader.setup()
    result = reader.scan_codebase()

    assert isinstance(result["tree"], str)
    assert len(result["tree"].strip()) > 0, "tree should not be blank"


def test_scan_test_signals_has_expected_shape():
    """test_signals must always have 'has_tests' and 'framework' keys."""
    reader = ReaderAgent(".")
    reader.setup()
    result = reader.scan_codebase()

    ts = result["test_signals"]
    assert isinstance(ts, dict), "test_signals should be a dict"
    assert "has_tests" in ts
    assert "framework" in ts
    assert isinstance(ts["has_tests"], bool)


def test_scan_version_info_has_expected_shape():
    """version_info must always have 'version' key."""
    reader = ReaderAgent(".")
    reader.setup()
    result = reader.scan_codebase()

    vi = result["version_info"]
    assert isinstance(vi, dict), "version_info should be a dict"
    assert "version" in vi


def test_scan_external_api_calls_is_list():
    """external_api_calls must be a list (possibly empty)."""
    reader = ReaderAgent(".")
    reader.setup()
    result = reader.scan_codebase()

    assert isinstance(result["external_api_calls"], list)


def test_reader_cleanup_is_idempotent():
    """cleanup() should not raise even if called multiple times."""
    reader = ReaderAgent(".")
    reader.setup()
    reader.scan_codebase()
    reader.cleanup()
    reader.cleanup()  # should not raise
