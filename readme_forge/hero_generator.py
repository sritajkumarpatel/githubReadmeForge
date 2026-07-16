import os
from pathlib import Path

class HeroGenerator:
    def __init__(self, project_name, project_persona, tech_stack):
        self.project_name = project_name or "Project"
        self.project_persona = project_persona or "An automated developer codebase project."
        self.tech_stack = tech_stack or []

    def generate(self, output_dir):
        """Generates both dark and light hero SVG files in the specified directory."""
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        dark_svg = self._build_svg(is_dark=True)
        light_svg = self._build_svg(is_dark=False)

        dark_file = out_path / "hero-dark.svg"
        light_file = out_path / "hero-light.svg"

        dark_file.write_text(dark_svg, encoding="utf-8")
        light_file.write_text(light_svg, encoding="utf-8")

        return str(dark_file), str(light_file)

    def _build_svg(self, is_dark=True):
        # Canvas dimensions
        width = 1200
        height = 420

        # Style themes
        if is_dark:
            bg_gradient = """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#0b0f19" />
                <stop offset="50%" stop-color="#111827" />
                <stop offset="100%" stop-color="#1e1035" />
            </linearGradient>
            <radialGradient id="glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.15" />
                <stop offset="100%" stop-color="#3b82f6" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="glow-purple" cx="80%" cy="20%" r="40%">
                <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.12" />
                <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0" />
            </radialGradient>
            """
            title_color = "#ffffff"
            title_glow = "filter: drop-shadow(0px 0px 8px rgba(96, 165, 250, 0.4));"
            desc_color = "#9ca3af"
            grid_color = "rgba(255, 255, 255, 0.03)"
            badge_bg = "rgba(59, 130, 246, 0.1)"
            badge_border = "rgba(59, 130, 246, 0.3)"
            badge_text = "#60a5fa"
            accent_line = "url(#accent-gradient)"
            accent_gradient = """
            <linearGradient id="accent-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#3b82f6" />
                <stop offset="50%" stop-color="#8b5cf6" />
                <stop offset="100%" stop-color="#ec4899" />
            </linearGradient>
            """
        else:
            bg_gradient = """
            <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#ffffff" />
                <stop offset="50%" stop-color="#f8fafc" />
                <stop offset="100%" stop-color="#eef2f6" />
            </linearGradient>
            <radialGradient id="glow" cx="50%" cy="50%" r="50%">
                <stop offset="0%" stop-color="#3b82f6" stop-opacity="0.06" />
                <stop offset="100%" stop-color="#3b82f6" stop-opacity="0" />
            </radialGradient>
            <radialGradient id="glow-purple" cx="80%" cy="20%" r="40%">
                <stop offset="0%" stop-color="#8b5cf6" stop-opacity="0.05" />
                <stop offset="100%" stop-color="#8b5cf6" stop-opacity="0" />
            </radialGradient>
            """
            title_color = "#0f172a"
            title_glow = ""
            desc_color = "#475569"
            grid_color = "rgba(15, 23, 42, 0.02)"
            badge_bg = "rgba(59, 130, 246, 0.05)"
            badge_border = "rgba(59, 130, 246, 0.2)"
            badge_text = "#2563eb"
            accent_line = "url(#accent-gradient)"
            accent_gradient = """
            <linearGradient id="accent-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                <stop offset="0%" stop-color="#2563eb" />
                <stop offset="50%" stop-color="#7c3aed" />
                <stop offset="100%" stop-color="#db2777" />
            </linearGradient>
            """

        # Wrap description/persona
        desc_lines = self._wrap_text(self.project_persona, max_chars=75)
        desc_y_start = 185
        desc_y_offset = 26
        desc_tspans = ""
        for i, line in enumerate(desc_lines[:3]): # Max 3 lines to fit layout
            y = desc_y_start + (i * desc_y_offset)
            desc_tspans += f'<tspan x="600" y="{y}">{self._escape_xml(line)}</tspan>\n'

        # Tech stack badges layout
        # Estimate width of badge based on name length
        badges_y = 280
        badges_elements = ""
        
        # Calculate horizontal positions to center the row
        badge_spacing = 14
        total_width = 0
        badge_sizes = []
        for tech in self.tech_stack[:7]: # Show max 7 badges
            badge_w = max(len(tech) * 9 + 28, 70)
            badge_sizes.append((tech, badge_w))
            total_width += badge_w + badge_spacing
            
        if total_width > 0:
            total_width -= badge_spacing # Remove trailing spacing
            current_x = (width - total_width) / 2
            for tech, badge_w in badge_sizes:
                badges_elements += f"""
                <g transform="translate({current_x}, {badges_y})">
                    <rect width="{badge_w}" height="32" rx="16" fill="{badge_bg}" stroke="{badge_border}" stroke-width="1.5" />
                    <text x="{badge_w/2}" y="20" font-family="'Outfit', -apple-system, sans-serif" font-size="13" font-weight="600" fill="{badge_text}" text-anchor="middle">{self._escape_xml(tech)}</text>
                </g>
                """
                current_x += badge_w + badge_spacing

        # Base grid paths
        grid_paths = ""
        for i in range(50, width, 100):
            grid_paths += f'<line x1="{i}" y1="0" x2="{i}" y2="{height}" stroke="{grid_color}" stroke-width="1" />\n'
        for i in range(50, height, 80):
            grid_paths += f'<line x1="0" y1="{i}" x2="{width}" y2="{i}" stroke="{grid_color}" stroke-width="1" />\n'

        # Compile SVG
        svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" height="100%">
    <defs>
        {bg_gradient}
        {accent_gradient}
        <style>
            .title {{
                font-family: 'Outfit', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 54px;
                font-weight: 800;
                fill: {title_color};
                {title_glow}
            }}
            .desc {{
                font-family: 'Outfit', -apple-system, BlinkMacSystemFont, sans-serif;
                font-size: 18px;
                font-weight: 400;
                fill: {desc_color};
                letter-spacing: -0.01em;
            }}
        </style>
    </defs>

    <!-- Background -->
    <rect width="{width}" height="{height}" fill="url(#bg)" />

    <!-- Ambient Lights / Glows -->
    <circle cx="600" cy="210" r="500" fill="url(#glow)" />
    <circle cx="1000" cy="80" r="400" fill="url(#glow-purple)" />

    <!-- Grid Layout Lines -->
    {grid_paths}

    <!-- Top Design Element Accent Line -->
    <rect x="0" y="0" width="{width}" height="6" fill="{accent_line}" />

    <!-- Tech Stack / Code Interface Style Overlay (decorative dots) -->
    <circle cx="35" cy="35" r="6" fill="#ef4444" opacity="0.8" />
    <circle cx="55" cy="35" r="6" fill="#f59e0b" opacity="0.8" />
    <circle cx="75" cy="35" r="6" fill="#10b981" opacity="0.8" />

    <!-- Visual Code brackets (decorative frames) -->
    <path d="M 120 140 L 70 140 L 70 280 L 120 280" fill="none" stroke="{grid_color}" stroke-width="2" />
    <path d="M 1080 140 L 1130 140 L 1130 280 L 1080 280" fill="none" stroke="{grid_color}" stroke-width="2" />

    <!-- Title -->
    <text x="600" y="130" text-anchor="middle" class="title">{self._escape_xml(self.project_name)}</text>

    <!-- Description (wrapped tspans) -->
    <text x="600" y="{desc_y_start}" text-anchor="middle" class="desc">
        {desc_tspans}
    </text>

    <!-- Badges Row -->
    {badges_elements}

    <!-- Footer decorative tag -->
    <text x="600" y="380" font-family="'JetBrains Mono', monospace" font-size="11" font-weight="600" fill="{desc_color}" opacity="0.4" text-anchor="middle">&lt;/docs forged&gt;</text>
</svg>
"""
        return svg

    def _wrap_text(self, text, max_chars=75):
        """Splits a string into lines of maximum length without breaking words."""
        words = text.split()
        lines = []
        current_line = []
        current_len = 0

        for word in words:
            if current_len + len(word) + 1 <= max_chars:
                current_line.append(word)
                current_len += len(word) + 1
            else:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_len = len(word)

        if current_line:
            lines.append(" ".join(current_line))

        return lines

    def _escape_xml(self, text):
        """Escapes special XML characters."""
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;")
