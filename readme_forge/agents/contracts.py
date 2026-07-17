"""Contracts and deterministic planning helpers for the README agent pipeline.

These helpers deliberately use only the standard library.  They form a stable
boundary between best-effort LLM output and the writer, which must not need to
guess what a malformed analysis response means.
"""

from __future__ import annotations

from typing import Any


# "demo" — showcase/example apps that are not tutorials.
# "unknown" — analysis failed or confidence too low to classify meaningfully.
PROJECT_TYPES = {"learning", "poc", "demo", "library", "application", "cli", "api", "minimal", "unknown"}
MATURITY_LEVELS = {"production", "development", "poc", "unknown"}

# Maps each primary_intent to the best-fitting visual asset strategy.
# Used by WriterAgent to auto-select the SVG pack without requiring user input.
INTENT_VISUAL_STRATEGY: dict[str, str] = {
    "application": "ui_app",
    "demo":        "ui_app",
    "api":         "api",
    "library":     "package",
    "cli":         "package",
    "learning":    "minimal",
    "poc":         "minimal",
    "minimal":     "minimal",
    "unknown":     "minimal",
}


def _as_string_list(value: Any) -> list[str]:
    """Return a clean list of non-empty strings without inventing values."""
    if not isinstance(value, list):
        return []
    return [item.strip() for item in value if isinstance(item, str) and item.strip()]


def _as_dict_list(value: Any) -> list[dict[str, Any]]:
    """Keep only structured items expected by downstream documentation code."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def classify_repository(scan_results: dict[str, Any]) -> dict[str, Any]:
    """Classify repository surfaces from deterministic, inspectable signals.

    A repository can be both a package and a CLI/API.  This intentionally
    reports those independently instead of asking one LLM label to carry all
    documentation decisions.

    Returns a dict with:
      primary_intent    — one of PROJECT_TYPES
      delivery_surfaces — subset of {"package", "cli", "api", "ui"}
      maturity          — one of MATURITY_LEVELS
      confidence        — float 0.0–1.0
      evidence          — list of {"claim", "source", "signal"} dicts
    """
    configs = scan_results.get("configs", {})
    code_context = scan_results.get("code_context", {})
    tree = str(scan_results.get("tree", "")).lower()
    joined_code = "\n".join(
        str(content).lower() for content in code_context.values() if isinstance(content, str)
    )
    config_names = set(configs) if isinstance(configs, dict) else set()
    evidence: list[dict[str, str]] = []
    surfaces: list[str] = []

    def add_surface(name: str, source: str, signal: str) -> None:
        if name not in surfaces:
            surfaces.append(name)
        evidence.append({"claim": f"surface:{name}", "source": source, "signal": signal})

    # ── Detect delivery surfaces ──────────────────────────────────────────
    package_files = {"pyproject.toml", "setup.py", "package.json", "Cargo.toml", "go.mod"}
    for file_name in sorted(package_files & config_names):
        add_surface("package", file_name, "package manifest detected")

    cli_signals = ("argparse", "click.command", "@app.command", "typer", "sys.argv", "commander")
    for signal in cli_signals:
        if signal in joined_code:
            add_surface("cli", "source code", signal)
            break

    api_signals = ("fastapi", "flask", "@app.route", "@router.", "express()", "app.get(", "app.post(")
    for signal in api_signals:
        if signal in joined_code:
            add_surface("api", "source code", signal)
            break

    ui_signals = ("react", "vue", "svelte", "streamlit", "gradio", "tkinter")
    for signal in ui_signals:
        if signal in joined_code or signal in tree:
            add_surface("ui", "source code" if signal in joined_code else "repository tree", signal)
            break
    else:
        # A plain HTML/JS dashboard is still a UI surface even without a named framework.
        ui_files = ("web/", "public/", "index.html", "app.js", "app.ts")
        for signal in ui_files:
            if signal in tree:
                add_surface("ui", "repository tree", signal)
                break

    # ── Derive primary intent ─────────────────────────────────────────────
    tutorial_terms = ("tutorial", "course", "exercise", "practice", "workshop")
    demo_terms = (
        "demo", "showcase", "showroom", "sample-app", "sample_app",
        "example-app", "example_app", "starter", "boilerplate", "template",
    )

    intent = "application"

    if any(term in tree for term in tutorial_terms):
        intent = "learning"
        evidence.append({
            "claim": "intent:learning",
            "source": "repository tree",
            "signal": "tutorial/course/exercise name pattern detected",
        })
    elif any(term in tree for term in demo_terms):
        intent = "demo"
        evidence.append({
            "claim": "intent:demo",
            "source": "repository tree",
            "signal": "demo/showcase/sample name pattern detected",
        })
    elif "ui" in surfaces:
        # Any UI surface → application first (overrides sparse code check)
        intent = "application"
    elif "api" in surfaces and "ui" not in surfaces:
        intent = "api"
    elif "cli" in surfaces and "ui" not in surfaces and "api" not in surfaces:
        intent = "cli"
    elif "package" in surfaces and not ({"cli", "api"} & set(surfaces)):
        intent = "library"
    elif len(code_context) <= 2 and not surfaces:
        # Only fall to minimal when there are genuinely very few files AND no surfaces detected
        intent = "minimal"
        evidence.append({
            "claim": "intent:minimal",
            "source": "source inventory",
            "signal": "two or fewer scanned source files and no surface signals",
        })

    # ── Maturity from test signals ────────────────────────────────────────
    maturity = "development"
    test_signals = scan_results.get("test_signals", {})
    if isinstance(test_signals, dict) and test_signals.get("has_tests"):
        evidence.append({
            "claim": "maturity:development",
            "source": "test signals",
            "signal": "test files detected",
        })
    else:
        maturity = "unknown"

    # ── Confidence — degrade when evidence is thin ────────────────────────
    raw_confidence = min(1.0, 0.35 + 0.15 * len(evidence))

    # Downgrade to "unknown" intent when confidence is too low and no surfaces found.
    if raw_confidence < 0.4 and not surfaces:
        intent = "unknown"
        evidence.append({
            "claim": "intent:unknown",
            "source": "classifier",
            "signal": "insufficient signals to classify repository",
        })

    return {
        "primary_intent": intent,
        "delivery_surfaces": surfaces,
        "maturity": maturity,
        "confidence": round(raw_confidence, 2),
        "evidence": evidence,
        "suggested_visual_strategy": INTENT_VISUAL_STRATEGY.get(intent, "ui_app"),
    }


def build_documentation_plan(analysis: dict[str, Any]) -> dict[str, Any]:
    """Choose README sections from validated facts instead of prompt defaults."""
    classification = analysis.get("classification", {})
    if not isinstance(classification, dict):
        classification = {}
    intent = classification.get("primary_intent", analysis.get("project_type", "application"))
    surfaces = _as_string_list(classification.get("delivery_surfaces", []))
    sections = ["title", "overview"]

    # Problem / solution only make sense for substantive project types.
    if intent not in {"learning", "minimal", "unknown"}:
        sections.extend(["problem", "solution"])

    # Demo and PoC get a shorter "demonstration" section instead of full problem/solution.
    # (They already got "problem" + "solution" above for poc/demo — that's intentional;
    # they just get brief versions per the writer instructions.)

    if analysis.get("installation_commands") or "package" in surfaces:
        sections.append("installation")
    if analysis.get("cli_commands") or "cli" in surfaces:
        sections.append("usage")
    if analysis.get("config_variables"):
        sections.append("configuration")
    if analysis.get("api_endpoints") or "api" in surfaces:
        sections.append("api_reference")
    if analysis.get("key_features"):
        sections.append("features")
    if analysis.get("connections") or analysis.get("architecture_layers"):
        sections.append("architecture")
    if analysis.get("data_models"):
        sections.append("data_models")
    if analysis.get("test_coverage", {}).get("has_tests"):
        sections.append("testing")
    sections.extend(["repository_structure", "contributing_license"])

    return {
        "version": 1,
        "sections": sections,
        "primary_intent": intent,
        "delivery_surfaces": surfaces,
        "include_architecture_diagram": len(_as_dict_list(analysis.get("connections"))) >= 2,
        "evidence_only": not bool(analysis.get("analysis_complete", True)),
        "suggested_visual_strategy": classification.get(
            "suggested_visual_strategy",
            INTENT_VISUAL_STRATEGY.get(intent, "ui_app"),
        ),
    }


def normalize_analysis(raw: Any, scan_results: dict[str, Any], analysis_complete: bool = True) -> dict[str, Any]:
    """Validate LLM analysis into a complete, backward-compatible contract."""
    raw = raw if isinstance(raw, dict) else {}
    classification = classify_repository(scan_results)
    raw_classification = raw.get("classification")
    if isinstance(raw_classification, dict):
        # Deterministic signals are authoritative for surfaces and evidence.
        # Allow the LLM to override intent only within the known type set.
        requested_intent = raw_classification.get("primary_intent")
        if requested_intent in PROJECT_TYPES:
            classification["primary_intent"] = requested_intent
            # Keep visual strategy consistent with (possibly LLM-overridden) intent.
            classification["suggested_visual_strategy"] = INTENT_VISUAL_STRATEGY.get(
                requested_intent,
                classification["suggested_visual_strategy"],
            )

    project_type = raw.get("project_type")
    if project_type not in PROJECT_TYPES:
        project_type = classification["primary_intent"]
    project_maturity = raw.get("project_maturity")
    if project_maturity not in MATURITY_LEVELS:
        project_maturity = classification["maturity"]

    normalized = {
        "project_name": raw.get("project_name") if isinstance(raw.get("project_name"), str) else "Project",
        "project_type": project_type,
        "project_type_reason": (
            raw.get("project_type_reason")
            if isinstance(raw.get("project_type_reason"), str)
            else "Derived from repository signals."
        ),
        "project_maturity": project_maturity,
        "tech_stack": _as_string_list(raw.get("tech_stack")),
        "project_persona": raw.get("project_persona") if isinstance(raw.get("project_persona"), str) else "",
        "problem_statement": raw.get("problem_statement") if isinstance(raw.get("problem_statement"), str) else "",
        "solution_narrative": raw.get("solution_narrative") if isinstance(raw.get("solution_narrative"), str) else "",
        "key_features": _as_dict_list(raw.get("key_features")),
        "api_endpoints": _as_dict_list(raw.get("api_endpoints")),
        "config_variables": _as_dict_list(raw.get("config_variables")),
        "cli_commands": _as_dict_list(raw.get("cli_commands")),
        "data_models": _as_dict_list(raw.get("data_models")),
        "installation_commands": _as_dict_list(raw.get("installation_commands")),
        "external_services": _as_string_list(raw.get("external_services")),
        "test_coverage": raw.get("test_coverage") if isinstance(raw.get("test_coverage"), dict) else {},
        "architecture_layers": _as_dict_list(raw.get("architecture_layers")),
        "improvements": _as_dict_list(raw.get("improvements")),
        "connections": _as_dict_list(raw.get("connections")),
        "classification": classification,
        "analysis_complete": analysis_complete,
    }
    normalized["test_coverage"].setdefault("has_tests", False)
    normalized["test_coverage"].setdefault("framework", "unknown")
    normalized["test_coverage"].setdefault("test_count", 0)
    normalized["test_coverage"].setdefault("description", "")
    normalized["documentation_plan"] = build_documentation_plan(normalized)
    return normalized
