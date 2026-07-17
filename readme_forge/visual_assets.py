"""Generate portable, evidence-backed visual assets for README output."""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


# Simple Icons is a convenient source for technology marks.  We retain a small
# explicit registry so a guessed technology name never becomes a guessed logo.
TECH_ICON_REGISTRY = {
    "python": ("Python", "python"),
    "javascript": ("JavaScript", "javascript"),
    "typescript": ("TypeScript", "typescript"),
    "react": ("React", "react"),
    "vue": ("Vue.js", "vuedotjs"),
    "node.js": ("Node.js", "nodedotjs"),
    "node": ("Node.js", "nodedotjs"),
    "fastapi": ("FastAPI", "fastapi"),
    "flask": ("Flask", "flask"),
    "django": ("Django", "django"),
    "docker": ("Docker", "docker"),
    "kubernetes": ("Kubernetes", "kubernetes"),
    "postgresql": ("PostgreSQL", "postgresql"),
    "mysql": ("MySQL", "mysql"),
    "mongodb": ("MongoDB", "mongodb"),
    "redis": ("Redis", "redis"),
    "openai": ("OpenAI", "openai"),
    "gemini": ("Google Gemini", "googlegemini"),
    "anthropic": ("Anthropic", "anthropic"),
    "ollama": ("Ollama", "ollama"),
    "github actions": ("GitHub Actions", "githubactions"),
    "pytest": ("pytest", "pytest"),
}


def _short_label(value: str, limit: int = 24) -> str:
    value = " ".join(value.split())
    return value if len(value) <= limit else f"{value[:limit - 1].rstrip()}…"


def select_component_flow(connections: Any, max_nodes: int = 5) -> list[dict[str, str]]:
    """Return one readable critical path rather than every detected edge.

    README diagrams should explain the central user journey, not mirror a full
    dependency graph.  We prefer a root-to-leaf path and keep at most four
    relationships (five cards), with labels only when the analyzer supplied one.
    """
    edges = []
    for item in connections if isinstance(connections, list) else []:
        if not isinstance(item, dict):
            continue
        source = str(item.get("from", "")).strip()
        target = str(item.get("to", "")).strip()
        if source and target and source != target:
            edges.append({
                "from": _short_label(source),
                "to": _short_label(target),
                "relationship": _short_label(str(item.get("relationship", "")).strip(), 32),
            })
    if not edges:
        return []

    inbound = {edge["to"] for edge in edges}
    roots = [edge["from"] for edge in edges if edge["from"] not in inbound]
    current = roots[0] if roots else edges[0]["from"]
    path: list[dict[str, str]] = []
    visited_nodes = {current}

    def remaining_depth(node: str, seen: set[str]) -> int:
        """Prefer branches that continue the core story over leaf helpers."""
        candidates = [edge for edge in edges if edge["from"] == node and edge["to"] not in seen]
        if not candidates:
            return 0
        return 1 + max(remaining_depth(edge["to"], seen | {edge["to"]}) for edge in candidates)

    while len(visited_nodes) < max_nodes:
        candidates = [edge for edge in edges if edge["from"] == current and edge["to"] not in visited_nodes]
        if not candidates:
            break
        # Prefer the branch with the most useful continuation, then edges that
        # explain the relationship. Python's stable max preserves source order.
        edge = max(
            candidates,
            key=lambda candidate: (remaining_depth(candidate["to"], visited_nodes | {candidate["to"]}), bool(candidate["relationship"])),
        )
        path.append(edge)
        current = edge["to"]
        visited_nodes.add(current)

    # Fallback: if resulting path has < 2 edges but original edges list has >= 2,
    # show the first N edges as-is to present a more complete picture.
    if len(path) < 2 and len(edges) >= 2:
        return edges[:max_nodes - 1]

    return path


class VisualAssetGenerator:
    """Builds a self-contained visual package beside a generated README."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.assets_dir = self.output_dir / "assets" / "readme"

    def generate(
        self,
        analysis: dict[str, Any],
        strategy: str = "ui_app",
        no_external_assets: bool = False,
    ) -> dict[str, Any]:
        """Write the visual package and return stable README references."""
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        project_name = _short_label(str(analysis.get("project_name") or "Project"), 44)
        persona = _short_label(str(analysis.get("project_persona") or "Verified project documentation"), 92)
        flow = select_component_flow(analysis.get("connections", []))

        # Handle minimal strategy (no heavy banner files)
        if strategy == "minimal":
            return {
                "brand_light": "",
                "brand_dark": "",
                "architecture": "",
                "technology_icons": [],
                "attributions": "",
                "component_flow": [],
            }

        # Build strategy-specific hero SVG
        (self.assets_dir / "brand-light.svg").write_text(
            self._brand_svg(project_name, persona, strategy=strategy, dark=False), encoding="utf-8"
        )
        (self.assets_dir / "brand-dark.svg").write_text(
            self._brand_svg(project_name, persona, strategy=strategy, dark=True), encoding="utf-8"
        )

        if flow:
            (self.assets_dir / "architecture.svg").write_text(
                self._architecture_svg(flow), encoding="utf-8"
            )

        icons = [] if no_external_assets else self._technology_icons(analysis.get("tech_stack", []))
        if icons:
            (self.assets_dir / "ATTRIBUTIONS.md").write_text(self._attributions(icons), encoding="utf-8")

        return {
            "brand_light": "assets/readme/brand-light.svg",
            "brand_dark": "assets/readme/brand-dark.svg",
            "architecture": "assets/readme/architecture.svg" if flow else "",
            "technology_icons": icons,
            "attributions": "assets/readme/ATTRIBUTIONS.md" if icons else "",
            "component_flow": flow,
        }

    def markdown_intro(self, assets: dict[str, Any], no_external_assets: bool = False) -> str:
        """Return a GitHub-safe visual header assembled from generated assets."""
        if not assets.get("brand_light"):
            return ""
        lines = [
            "<picture>",
            f'  <source media="(prefers-color-scheme: dark)" srcset="{assets["brand_dark"]}">',
            f'  <img alt="Project visual identity" src="{assets["brand_light"]}" width="100%">',
            "</picture>",
        ]
        icons = assets.get("technology_icons", [])
        if icons and not no_external_assets:
            lines.extend(["", '<p align="center">'])
            for icon in icons:
                lines.append(
                    f'  <img src="https://cdn.simpleicons.org/{icon["slug"]}" '
                    f'height="34" alt="{escape(icon["name"])}" title="{escape(icon["name"])}">'
                )
            lines.extend(["</p>", ""])
        if assets.get("architecture"):
            lines.extend([
                "",
                "<p align=\"center\">",
                f'  <img alt="Concise architecture flow" src="{assets["architecture"]}" width="100%">',
                "</p>",
            ])
        return "\n".join(lines)

    def _technology_icons(self, tech_stack: Any) -> list[dict[str, str]]:
        icons = []
        seen = set()
        for technology in tech_stack if isinstance(tech_stack, list) else []:
            if not isinstance(technology, str):
                continue
            normalized = technology.lower().strip()
            match = next((item for key, item in TECH_ICON_REGISTRY.items() if key in normalized), None)
            if match and match[1] not in seen:
                seen.add(match[1])
                icons.append({"name": match[0], "slug": match[1]})
        return icons[:6]

    def _brand_svg(self, project_name: str, persona: str, strategy: str, dark: bool) -> str:
        background = "#0b1020" if dark else "#f7f9fc"
        primary = "#f4f7ff" if dark else "#14213d"
        muted = "#b7c2e2" if dark else "#52627e"
        card = "#141c33" if dark else "#ffffff"

        if strategy == "ui_app":
            # Storyboard / UI panel composition
            return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280" viewBox="0 0 1200 280" role="img" aria-label="{escape(project_name)}">
  <rect width="1200" height="280" fill="{background}"/>
  <rect x="58" y="32" width="1084" height="216" rx="10" fill="{card}" stroke="{muted}" stroke-width="1" opacity="0.85"/>
  <rect x="58" y="32" width="1084" height="34" rx="10" fill="{primary}" opacity="0.08"/>
  <circle cx="82" cy="49" r="5" fill="#ff5f56"/>
  <circle cx="98" cy="49" r="5" fill="#ffbd2e"/>
  <circle cx="114" cy="49" r="5" fill="#27c93f"/>
  <rect x="76" y="80" width="190" height="150" rx="6" fill="{background}" stroke="{muted}" stroke-width="1" opacity="0.5"/>
  <rect x="290" y="80" width="828" height="150" rx="6" fill="{background}" stroke="{muted}" stroke-width="1" opacity="0.5"/>
  <text x="318" y="132" fill="{primary}" font-family="Arial, Helvetica, sans-serif" font-size="36" font-weight="700">{escape(project_name)}</text>
  <text x="318" y="168" fill="{muted}" font-family="Arial, Helvetica, sans-serif" font-size="17">{escape(persona)}</text>
  <rect x="318" y="192" width="140" height="26" rx="13" fill="#6d5dfc" opacity="0.9"/>
  <text x="388" y="209" fill="#ffffff" font-family="Arial, sans-serif" font-size="11" font-weight="bold" text-anchor="middle">UI Application</text>
</svg>'''

        elif strategy == "api":
            # API Request-Response flow composition
            arrow_color = "#6d5dfc"
            green_arrow = "#00c2a8"
            return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280" viewBox="0 0 1200 280" role="img" aria-label="{escape(project_name)}">
  <defs>
    <marker id="arrow-green" markerWidth="8" markerHeight="8" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="{green_arrow}"/></marker>
    <marker id="arrow-purple" markerWidth="8" markerHeight="8" refX="5" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" fill="{arrow_color}"/></marker>
  </defs>
  <rect width="1200" height="280" fill="{background}"/>
  <rect x="80" y="65" width="280" height="150" rx="12" fill="{card}" stroke="{muted}" stroke-width="1" opacity="0.7"/>
  <text x="220" y="105" text-anchor="middle" fill="{primary}" font-family="Arial, sans-serif" font-size="16" font-weight="700">HTTP Client Request</text>
  <rect x="110" y="130" width="220" height="28" rx="6" fill="#00c2a8" opacity="0.12"/>
  <text x="220" y="148" text-anchor="middle" fill="{primary}" font-family="Courier, monospace" font-size="12" font-weight="bold">GET /api/v1/resources</text>
  
  <path d="M 390 140 H 510" stroke="{arrow_color}" stroke-width="3" stroke-dasharray="5,5" marker-end="url(#arrow-purple)"/>
  <text x="450" y="125" text-anchor="middle" fill="{muted}" font-family="Arial, sans-serif" font-size="12">JSON Payload</text>

  <rect x="540" y="65" width="300" height="150" rx="12" fill="{card}" stroke="{muted}" stroke-width="1" opacity="0.7"/>
  <text x="690" y="105" text-anchor="middle" fill="{primary}" font-family="Arial, sans-serif" font-size="16" font-weight="700">API Router Gateway</text>
  <text x="690" y="142" text-anchor="middle" fill="{muted}" font-family="Arial, sans-serif" font-size="13">{escape(project_name)}</text>
  <text x="690" y="172" text-anchor="middle" fill="#6d5dfc" font-family="Arial, sans-serif" font-size="12" font-weight="bold">Routing &amp; Endpoints</text>

  <path d="M 870 140 H 990" stroke="{green_arrow}" stroke-width="3" marker-end="url(#arrow-green)"/>
  <text x="930" y="125" text-anchor="middle" fill="{muted}" font-family="Arial, sans-serif" font-size="12">Response 200 OK</text>
</svg>'''

        elif strategy == "package":
            # Code structure / Usage snippet motif
            return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280" viewBox="0 0 1200 280" role="img" aria-label="{escape(project_name)}">
  <rect width="1200" height="280" fill="{background}"/>
  <rect x="60" y="40" width="1080" height="200" rx="10" fill="#0f172a" stroke="#1e293b" stroke-width="2"/>
  <circle cx="90" cy="65" r="5" fill="#ff5f56"/>
  <circle cx="106" cy="65" r="5" fill="#ffbd2e"/>
  <circle cx="122" cy="65" r="5" fill="#27c93f"/>
  <text x="90" y="115" fill="#38bdf8" font-family="Courier, monospace" font-size="16">import {escape(project_name.lower().replace(" ", "_"))}</text>
  <text x="90" y="150" fill="#e2e8f0" font-family="Courier, monospace" font-size="16">sdk = {escape(project_name.replace(" ", ""))}.initialize(api_key="sk_...")</text>
  <text x="90" y="185" fill="#34d399" font-family="Courier, monospace" font-size="16">result = sdk.execute(query_context)</text>
  <text x="90" y="215" fill="#94a3b8" font-family="Courier, monospace" font-size="13"># {escape(persona)}</text>
</svg>'''

        elif strategy == "data":
            # Chart/Schema/Data relationship motif
            return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280" viewBox="0 0 1200 280" role="img" aria-label="{escape(project_name)}">
  <rect width="1200" height="280" fill="{background}"/>
  <rect x="100" y="50" width="250" height="180" rx="8" fill="{card}" stroke="{muted}" stroke-width="1"/>
  <rect x="100" y="50" width="250" height="40" rx="8" fill="#6d5dfc" opacity="0.12"/>
  <text x="225" y="75" text-anchor="middle" fill="{primary}" font-family="Arial, sans-serif" font-weight="bold" font-size="14">Source Code Input</text>
  <text x="120" y="120" fill="{muted}" font-family="Arial, sans-serif" font-size="12">🗝️ id : INT</text>
  <text x="120" y="150" fill="{muted}" font-family="Arial, sans-serif" font-size="12">🔹 path : VARCHAR</text>
  <text x="120" y="180" fill="{muted}" font-family="Arial, sans-serif" font-size="12">🔹 content : TEXT</text>

  <path d="M 370 140 H 490" stroke="#6d5dfc" stroke-width="3" marker-end="url(#arrow)"/>

  <rect x="510" y="50" width="260" height="180" rx="8" fill="{card}" stroke="{muted}" stroke-width="1"/>
  <rect x="510" y="50" width="260" height="40" rx="8" fill="#00c2a8" opacity="0.12"/>
  <text x="640" y="75" text-anchor="middle" fill="{primary}" font-family="Arial, sans-serif" font-weight="bold" font-size="14">Analysis Output</text>
  <text x="530" y="120" fill="{muted}" font-family="Arial, sans-serif" font-size="12">🗝️ analysis_id : INT</text>
  <text x="530" y="150" fill="{muted}" font-family="Arial, sans-serif" font-size="12">🔹 sections : ARRAY</text>
  <text x="530" y="180" fill="{muted}" font-family="Arial, sans-serif" font-size="12">🔹 strategy : VARCHAR</text>
</svg>'''

        else:
            # Default fallback brand SVG
            return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280" viewBox="0 0 1200 280" role="img" aria-label="{escape(project_name)}">
  <rect width="1200" height="280" fill="{background}"/>
  <circle cx="1080" cy="48" r="210" fill="#6d5dfc" opacity=".18"/>
  <circle cx="1120" cy="258" r="170" fill="#00c2a8" opacity=".12"/>
  <rect x="58" y="52" width="116" height="116" rx="30" fill="{card}"/>
  <path d="M88 112 116 84l28 28-28 28z" fill="#6d5dfc"/>
  <path d="m116 84 28 28-28 28" fill="#00c2a8" opacity=".88"/>
  <text x="208" y="110" fill="{primary}" font-family="Arial, Helvetica, sans-serif" font-size="42" font-weight="700">{escape(project_name)}</text>
  <text x="208" y="151" fill="{muted}" font-family="Arial, Helvetica, sans-serif" font-size="21">{escape(persona)}</text>
  <rect x="208" y="185" width="240" height="5" rx="2.5" fill="#6d5dfc"/>
</svg>'''

    def _architecture_svg(self, flow: list[dict[str, str]]) -> str:
        nodes = [flow[0]["from"]] + [edge["to"] for edge in flow]
        width = max(760, 80 + 225 * len(nodes))
        cards = []
        arrows = []
        for index, node in enumerate(nodes):
            x = 40 + 225 * index
            cards.append(
                f'<rect x="{x}" y="82" width="170" height="88" rx="18" fill="#ffffff" stroke="#dbe4f0"/>'
                f'<text x="{x + 85}" y="123" text-anchor="middle" fill="#14213d" font-family="Arial, Helvetica, sans-serif" font-size="16" font-weight="700">{escape(node)}</text>'
            )
            if index < len(flow):
                arrow_x = x + 170
                label = flow[index]["relationship"]
                arrows.append(f'<path d="M {arrow_x + 10} 126 H {arrow_x + 45}" stroke="#6d5dfc" stroke-width="3" marker-end="url(#arrow)"/>')
                if label:
                    arrows.append(f'<text x="{arrow_x + 28}" y="104" text-anchor="middle" fill="#52627e" font-family="Arial, Helvetica, sans-serif" font-size="11">{escape(label)}</text>')
        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="250" viewBox="0 0 {width} 250" role="img" aria-label="Concise architecture flow">
  <defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0,0 L0,6 L9,3 z" fill="#6d5dfc"/></marker></defs>
  <rect width="100%" height="100%" rx="24" fill="#f7f9fc"/>
  <text x="40" y="48" fill="#14213d" font-family="Arial, Helvetica, sans-serif" font-size="20" font-weight="700">How the core flow works</text>
  <text x="40" y="70" fill="#52627e" font-family="Arial, Helvetica, sans-serif" font-size="13">A concise path through the most important components</text>
  {''.join(arrows)}
  {''.join(cards)}
</svg>'''

    def _attributions(self, icons: list[dict[str, str]]) -> str:
        names = ", ".join(icon["name"] for icon in icons)
        return (
            "# Technology icon attribution\n\n"
            f"This README references these technology marks: {names}.\n\n"
            "Icon source: [Simple Icons](https://simpleicons.org/) (CC0 project). "
            "Technology names and marks may be trademarks of their respective owners; "
            "their use here identifies the detected technology and does not imply endorsement.\n"
        )
