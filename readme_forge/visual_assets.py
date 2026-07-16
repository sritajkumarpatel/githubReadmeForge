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
    return path


class VisualAssetGenerator:
    """Builds a self-contained visual package beside a generated README."""

    def __init__(self, output_dir: Path):
        self.output_dir = Path(output_dir)
        self.assets_dir = self.output_dir / "assets" / "readme"

    def generate(self, analysis: dict[str, Any]) -> dict[str, Any]:
        """Write the visual package and return stable README references."""
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        project_name = _short_label(str(analysis.get("project_name") or "Project"), 44)
        persona = _short_label(str(analysis.get("project_persona") or "Verified project documentation"), 92)
        flow = select_component_flow(analysis.get("connections", []))

        (self.assets_dir / "brand-light.svg").write_text(
            self._brand_svg(project_name, persona, dark=False), encoding="utf-8"
        )
        (self.assets_dir / "brand-dark.svg").write_text(
            self._brand_svg(project_name, persona, dark=True), encoding="utf-8"
        )
        if flow:
            (self.assets_dir / "architecture.svg").write_text(
                self._architecture_svg(flow), encoding="utf-8"
            )

        icons = self._technology_icons(analysis.get("tech_stack", []))
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

    def markdown_intro(self, assets: dict[str, Any]) -> str:
        """Return a GitHub-safe visual header assembled from generated assets."""
        lines = [
            "<picture>",
            f'  <source media="(prefers-color-scheme: dark)" srcset="{assets["brand_dark"]}">',
            f'  <img alt="Project visual identity" src="{assets["brand_light"]}" width="100%">',
            "</picture>",
        ]
        icons = assets.get("technology_icons", [])
        if icons:
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

    def _brand_svg(self, project_name: str, persona: str, dark: bool) -> str:
        background = "#0b1020" if dark else "#f7f9fc"
        primary = "#f4f7ff" if dark else "#14213d"
        muted = "#b7c2e2" if dark else "#52627e"
        card = "#141c33" if dark else "#ffffff"
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
