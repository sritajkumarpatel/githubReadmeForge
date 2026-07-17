"""Generate portable, evidence-backed visual assets for README output."""

from __future__ import annotations

import urllib.parse
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

import re

def split_node_name(name: str) -> list[str]:
    """Split camelCase, PascalCase, or snake_case names into up to 3 readable lines."""
    tokens = re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z][a-z]|\b)|\d+|[a-zA-Z]+', name)
    if not tokens:
        return [name]
    
    lines = []
    current_line = ""
    for token in tokens:
        if not current_line:
            current_line = token
        elif len(current_line) + len(token) <= 12:
            current_line += token
        else:
            lines.append(current_line)
            current_line = token
    if current_line:
        lines.append(current_line)
    return lines[:3]


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
                name_encoded = urllib.parse.quote(icon["name"])
                lines.append(
                    f'  <img src="https://img.shields.io/badge/-{name_encoded}-555555?style=flat-square&logo={icon["slug"]}&logoColor=white" '
                    f'alt="{escape(icon["name"])}">'
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
        if strategy == "ui_app":
            bg = "#0f172a" if dark else "#f8fafc"
            primary_text = "#ffffff" if dark else "#0f172a"
            muted_text = "#94a3b8" if dark else "#475569"
            badge_bg = "#6d5dfc"
            accent_color = "#00c2a8"
            artwork = f'''
  <rect x="780" y="50" width="340" height="180" rx="12" fill="#1e293b" stroke="#334155" stroke-width="1.5"/>
  <circle cx="802" cy="68" r="5" fill="#ff5f56"/>
  <circle cx="818" cy="68" r="5" fill="#ffbd2e"/>
  <circle cx="834" cy="68" r="5" fill="#27c93f"/>
  <rect x="794" y="92" width="60" height="126" rx="6" fill="#0f172a" opacity="0.4"/>
  <rect x="866" y="92" width="242" height="60" rx="8" fill="#0f172a" opacity="0.6"/>
  <rect x="866" y="162" width="114" height="56" rx="8" fill="#0f172a" opacity="0.6"/>
  <rect x="994" y="162" width="114" height="56" rx="8" fill="{badge_bg}" opacity="0.3"/>
  <circle cx="1051" cy="190" r="16" fill="{accent_color}" opacity="0.8"/>
'''
        elif strategy == "api":
            bg = "#09090b" if dark else "#f4f4f5"
            primary_text = "#ffffff" if dark else "#09090b"
            muted_text = "#a1a1aa" if dark else "#71717a"
            badge_bg = "#00c2a8"
            accent_color = "#38bdf8"
            artwork = f'''
  <circle cx="950" cy="140" r="32" fill="{accent_color}" opacity="0.15" stroke="{accent_color}" stroke-width="1.5"/>
  <circle cx="950" cy="140" r="6" fill="{accent_color}"/>
  
  <line x1="950" y1="140" x2="860" y2="90" stroke="#475569" stroke-width="1.5"/>
  <line x1="950" y1="140" x2="1040" y2="90" stroke="#475569" stroke-width="1.5"/>
  <line x1="950" y1="140" x2="860" y2="190" stroke="#475569" stroke-width="1.5"/>
  <line x1="950" y1="140" x2="1040" y2="190" stroke="#475569" stroke-width="1.5"/>
  
  <circle cx="860" cy="90" r="14" fill="#1e293b" stroke="{badge_bg}" stroke-width="2"/>
  <circle cx="860" cy="90" r="4" fill="{badge_bg}"/>
  
  <circle cx="1040" cy="90" r="14" fill="#1e293b" stroke="{accent_color}" stroke-width="2"/>
  <circle cx="1040" cy="90" r="4" fill="{accent_color}"/>
  
  <circle cx="860" cy="190" r="14" fill="#1e293b" stroke="{accent_color}" stroke-width="2"/>
  <circle cx="860" cy="190" r="4" fill="{accent_color}"/>
  
  <circle cx="1040" cy="190" r="14" fill="#1e293b" stroke="{badge_bg}" stroke-width="2"/>
  <circle cx="1040" cy="190" r="4" fill="{badge_bg}"/>
  
  <circle cx="950" cy="140" r="75" fill="none" stroke="#475569" stroke-width="1.5" stroke-dasharray="6,6"/>
'''
        elif strategy == "package":
            bg = "#030712" if dark else "#f9fafb"
            primary_text = "#ffffff" if dark else "#111827"
            muted_text = "#9ca3af" if dark else "#4b5563"
            badge_bg = "#6d5dfc"
            accent_color = "#34d399"
            artwork = f'''
  <path d="M 830 80 L 780 140 L 830 200" fill="none" stroke="{accent_color}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <path d="M 1070 80 L 1120 140 L 1070 200" fill="none" stroke="#38bdf8" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <rect x="860" y="90" width="180" height="100" rx="16" fill="#1f2937" stroke="{badge_bg}" stroke-width="2.5"/>
  <text x="950" y="142" text-anchor="middle" fill="#ffffff" font-family="Courier, monospace" font-size="16" font-weight="bold">import sdk</text>
  <rect x="890" y="158" width="120" height="6" rx="3" fill="{accent_color}" opacity="0.8"/>
'''
        elif strategy == "data":
            bg = "#081b33" if dark else "#f0f4f8"
            primary_text = "#ffffff" if dark else "#0f2d4a"
            muted_text = "#9ab6d6" if dark else "#4a6b82"
            badge_bg = "#38bdf8"
            accent_color = "#ffffff"
            artwork = f'''
  <rect x="790" y="60" width="130" height="110" rx="8" fill="#111c30" stroke="#38bdf8" stroke-width="1.5"/>
  <rect x="790" y="60" width="130" height="28" rx="8" fill="#38bdf8" opacity="0.2"/>
  <line x1="790" y1="88" x2="920" y2="88" stroke="#38bdf8" stroke-width="1.5"/>
  <line x1="790" y1="116" x2="920" y2="116" stroke="#1d2e4a"/>
  <line x1="790" y1="144" x2="920" y2="144" stroke="#1d2e4a"/>
  <circle cx="810" cy="74" r="4" fill="#38bdf8"/>
  
  <rect x="970" y="110" width="130" height="110" rx="8" fill="#111c30" stroke="#00c2a8" stroke-width="1.5"/>
  <rect x="970" y="110" width="130" height="28" rx="8" fill="#00c2a8" opacity="0.2"/>
  <line x1="970" y1="138" x2="1100" y2="138" stroke="#00c2a8" stroke-width="1.5"/>
  <line x1="970" y1="166" x2="1100" y2="166" stroke="#1d2e4a"/>
  <line x1="970" y1="194" x2="1100" y2="194" stroke="#1d2e4a"/>
  <circle cx="990" cy="124" r="4" fill="#00c2a8"/>
  
  <path d="M 920 115 H 970" stroke="{badge_bg}" stroke-width="2.5" stroke-dasharray="4,4"/>
  <circle cx="920" cy="115" r="4" fill="{badge_bg}"/>
  <circle cx="970" cy="115" r="4" fill="{badge_bg}"/>
'''
        else:
            bg = "#faf9f6" if not dark else "#0c0a09"
            primary_text = "#1c1917" if not dark else "#f5f5f4"
            muted_text = "#78716c" if not dark else "#a8a29e"
            badge_bg = "#ea580c"
            accent_color = "#3b82f6"
            artwork = f'''
  <path d="M 760 170 Q 860 50 960 170 T 1160 50" fill="none" stroke="{badge_bg}" stroke-width="4.5" stroke-linecap="round"/>
  <circle cx="960" cy="170" r="7" fill="{accent_color}" stroke="#ffffff" stroke-width="2.5"/>
  <circle cx="860" cy="90" r="7" fill="#ff5f56" stroke="#ffffff" stroke-width="2.5"/>
  <circle cx="1060" cy="90" r="7" fill="#ffbd2e" stroke="#ffffff" stroke-width="2.5"/>
'''

        strategy_label = strategy.upper().replace("_", " ")
        if strategy_label == "UI APP":
            strategy_label = "UI APPLICATION"

        return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="280" viewBox="0 0 1200 280" role="img" aria-label="{escape(project_name)}">
  <rect width="1200" height="280" fill="{bg}"/>
  
  <text x="60" y="110" fill="{primary_text}" font-family="system-ui, -apple-system, sans-serif" font-size="48" font-weight="800">{escape(project_name)}</text>
  <text x="60" y="152" fill="{muted_text}" font-family="system-ui, -apple-system, sans-serif" font-size="18" font-weight="400">{escape(persona)}</text>
  
  <rect x="60" y="182" width="180" height="28" rx="14" fill="{badge_bg}" opacity="0.85"/>
  <text x="150" y="200" fill="#ffffff" font-family="system-ui, -apple-system, sans-serif" font-size="11" font-weight="bold" text-anchor="middle">{strategy_label}</text>
  
  {artwork}
</svg>'''

    def _architecture_svg(self, flow: list[dict[str, str]]) -> str:
        nodes = [flow[0]["from"]] + [edge["to"] for edge in flow]
        width = max(760, 80 + 225 * len(nodes))
        cards = []
        arrows = []
        for index, node in enumerate(nodes):
            x = 40 + 225 * index
            node_lines = split_node_name(node)
            cards.append(f'<rect x="{x}" y="82" width="170" height="88" rx="18" fill="#ffffff" stroke="#dbe4f0" stroke-width="1.5"/>')
            if len(node_lines) == 1:
                cards.append(f'<text x="{x + 85}" y="131" text-anchor="middle" fill="#14213d" font-family="Arial, Helvetica, sans-serif" font-size="14" font-weight="700">{escape(node_lines[0])}</text>')
            elif len(node_lines) == 2:
                cards.append(
                    f'<text x="{x + 85}" y="122" text-anchor="middle" fill="#14213d" font-family="Arial, Helvetica, sans-serif" font-size="12" font-weight="700">{escape(node_lines[0])}</text>'
                    f'<text x="{x + 85}" y="142" text-anchor="middle" fill="#14213d" font-family="Arial, Helvetica, sans-serif" font-size="12" font-weight="700">{escape(node_lines[1])}</text>'
                )
            else:
                cards.append(
                    f'<text x="{x + 85}" y="114" text-anchor="middle" fill="#14213d" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="700">{escape(node_lines[0])}</text>'
                    f'<text x="{x + 85}" y="132" text-anchor="middle" fill="#14213d" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="700">{escape(node_lines[1])}</text>'
                    f'<text x="{x + 85}" y="150" text-anchor="middle" fill="#14213d" font-family="Arial, Helvetica, sans-serif" font-size="10.5" font-weight="700">{escape(node_lines[2])}</text>'
                )
            if index < len(flow):
                arrow_x = x + 170
                label = flow[index]["relationship"]
                arrows.append(f'<path d="M {arrow_x + 8} 126 H {arrow_x + 47}" stroke="#6d5dfc" stroke-width="3" marker-end="url(#arrow)"/>')
                if label:
                    short_label = label[:14] + "..." if len(label) > 14 else label
                    arrows.append(f'<text x="{arrow_x + 27}" y="106" text-anchor="middle" fill="#52627e" font-family="Arial, Helvetica, sans-serif" font-size="9">{escape(short_label)}</text>')
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
