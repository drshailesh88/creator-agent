#!/usr/bin/env python3
"""
LaTeX Graphics Generator

Generates branded infographics, presentations, and documents using LaTeX/TikZ.
"""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime

# Path to LaTeX templates
TEMPLATE_DIR = Path(__file__).parent.parent.parent / "latex"


class LaTeXGenerator:
    """Generate LaTeX documents with brand styling."""

    # FontAwesome icon mapping for common concepts
    ICONS = {
        "heart": r"\faHeart",
        "brain": r"\faBrain",
        "running": r"\faRunning",
        "chart": r"\faChartLine",
        "globe": r"\faGlobe",
        "user": r"\faUser",
        "doctor": r"\faUserMd",
        "check": r"\faCheck",
        "warning": r"\faExclamationTriangle",
        "info": r"\faInfoCircle",
        "lightbulb": r"\faLightbulb",
        "star": r"\faStar",
        "clock": r"\faClock",
        "calendar": r"\faCalendar",
        "pill": r"\faPills",
        "stethoscope": r"\faStethoscope",
        "heartbeat": r"\faHeartbeat",
        "ambulance": r"\faAmbulance",
        "hospital": r"\faHospital",
        "thermometer": r"\faThermometerHalf",
    }

    def __init__(self, output_dir: Optional[str] = None):
        """Initialize the generator."""
        self.output_dir = Path(output_dir) if output_dir else Path(tempfile.mkdtemp())
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Copy brand files to output directory
        self._setup_brand_files()

    def _setup_brand_files(self) -> None:
        """Copy brand style files to output directory."""
        brand_files = [
            TEMPLATE_DIR / "brand-colors.sty",
            TEMPLATE_DIR / "infographics" / "components.sty",
            TEMPLATE_DIR / "presentations" / "beamer-theme.sty",
        ]

        for src in brand_files:
            if src.exists():
                dst = self.output_dir / src.name
                dst.write_text(src.read_text())

    def _get_icon(self, name: str) -> str:
        """Get FontAwesome icon command."""
        return self.ICONS.get(name.lower(), r"\faCircle")

    def create_infographic(
        self,
        title: str,
        infographic_type: str,
        content: Dict[str, Any],
        subtitle: str = "",
        output_name: str = "infographic",
    ) -> Path:
        """
        Generate an infographic.

        Args:
            title: Main title
            infographic_type: Type (medical, statistics, process, etc.)
            content: Content dictionary with stats, sections, steps, alert
            subtitle: Optional subtitle
            output_name: Output filename (without extension)

        Returns:
            Path to generated .tex file
        """
        # Build the infographic content
        tikz_content = self._build_infographic_content(infographic_type, content)

        tex_code = rf"""% Auto-generated infographic
% Compile with: pdflatex {output_name}.tex

\documentclass[tikz,border=10pt]{{standalone}}

\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{tikz}}
\usepackage{{fontawesome5}}

\usetikzlibrary{{
    shapes.geometric,
    shapes.symbols,
    arrows.meta,
    positioning,
    calc,
    fit,
    backgrounds,
    shadows.blur,
    decorations.pathreplacing
}}

\usepackage{{brand-colors}}
\usepackage{{components}}

\begin{{document}}
\begin{{tikzpicture}}[remember picture]

% Background
\fill[BrandBackground] (-0.5,-1) rectangle (16,14);

% Header bar
\fill[BrandPrimary] (-0.5,12.5) rectangle (16,14);

% Title
\node[font=\sffamily\bfseries\Huge, text=white] at (8,13.5) {{{title}}};
\node[font=\sffamily, text=white!90] at (8,12.8) {{{subtitle}}};

{tikz_content}

% Footer
\node[font=\sffamily\tiny, text=BrandText!60] at (8,-0.5) {{Created with DrShailesh Brand System | \today}};

\end{{tikzpicture}}
\end{{document}}
"""

        output_path = self.output_dir / f"{output_name}.tex"
        output_path.write_text(tex_code)
        return output_path

    def _build_infographic_content(
        self,
        infographic_type: str,
        content: Dict[str, Any]
    ) -> str:
        """Build TikZ content based on infographic type."""
        parts = []

        # Stats row
        if "stats" in content:
            parts.append(self._build_stats_row(content["stats"]))

        # Sections (like risk factors, checklist)
        if "sections" in content:
            parts.append(self._build_sections(content["sections"]))

        # Process steps
        if "steps" in content:
            parts.append(self._build_steps(content["steps"]))

        # Alert box
        if "alert" in content:
            parts.append(self._build_alert(content["alert"]))

        return "\n\n".join(parts)

    def _build_stats_row(self, stats: List[Dict]) -> str:
        """Build a row of stat boxes."""
        lines = [r"% Statistics row"]
        lines.append(r"\node[font=\sffamily\bfseries, text=BrandPrimary] at (1,11.5) {Key Facts};")

        # Calculate positions
        num_stats = len(stats)
        spacing = 14 / (num_stats + 1)

        for i, stat in enumerate(stats):
            x = spacing * (i + 1) + 1
            icon = self._get_icon(stat.get("icon", "circle"))
            value = stat.get("value", "")
            label = stat.get("label", "")
            lines.append(rf"\iconstat{{{x}}}{{10}}{{{icon}}}{{{value}}}{{{label}}}")

        return "\n".join(lines)

    def _build_sections(self, sections: List[Dict]) -> str:
        """Build content sections."""
        lines = [r"% Content sections"]

        y_offset = 8
        x_positions = [0, 9]  # Two columns

        for i, section in enumerate(sections):
            x = x_positions[i % 2]
            title = section.get("title", "")
            items = section.get("items", [])

            # Section box
            lines.append(rf"""
\node[
    brand box,
    minimum width=7cm,
    minimum height=5cm,
    anchor=north west
] at ({x},{y_offset}) {{}};
\node[font=\sffamily\bfseries\large, text=BrandPrimary, anchor=north west] at ({x+0.3},{y_offset-0.3}) {{{title}}};
""")

            # Items
            item_y = y_offset - 1.2
            for item in items[:7]:  # Limit items
                lines.append(rf"\checkitem{{{x+0.5}}}{{{item_y}}}{{{item}}}{{1}}")
                item_y -= 0.6

            if i % 2 == 1:
                y_offset -= 5.5

        return "\n".join(lines)

    def _build_steps(self, steps: List[Dict]) -> str:
        """Build process steps."""
        lines = [r"% Process steps"]

        y = 4
        x_spacing = 4.5

        for i, step in enumerate(steps):
            x = 1 + (i * x_spacing)
            num = step.get("number", i + 1)
            title = step.get("title", "")
            desc = step.get("description", "")[:50]  # Truncate

            lines.append(rf"\stepbox{{{x}}}{{{y}}}{{{num}}}{{{title}}}{{{desc}}}")

        return "\n".join(lines)

    def _build_alert(self, alert: Dict) -> str:
        """Build alert box."""
        title = alert.get("title", "Warning")
        items = alert.get("items", [])

        items_tex = " ".join([
            rf"\node[font=\sffamily\small, text=BrandText] at ({3 + i*3.5},1.1) {{\faTimesCircle\ {item}}};"
            for i, item in enumerate(items[:4])
        ])

        return rf"""
% Alert section
\node[
    alert box,
    minimum width=15.5cm,
    minimum height=2.2cm,
    anchor=north
] at (8,2.3) {{}};

\node[font=\sffamily\bfseries\large, text=BrandAlert] at (8,1.9) {{\faExclamationTriangle\quad {title}}};

{items_tex}

\node[font=\sffamily\bfseries, text=BrandAlert] at (8,0.4) {{Call Emergency Services Immediately}};
"""

    def create_presentation(
        self,
        title: str,
        slides: List[Dict[str, Any]],
        subtitle: str = "",
        author: str = "Dr. Shailesh",
        output_name: str = "presentation",
    ) -> Path:
        """Generate a Beamer presentation."""

        slides_tex = self._build_slides(slides)

        tex_code = rf"""\documentclass[aspectratio=169]{{beamer}}

\usepackage[utf8]{{inputenc}}
\usepackage[T1]{{fontenc}}
\usepackage{{fontawesome5}}
\usepackage{{brand-colors}}
\usepackage{{beamer-theme}}

\title{{{title}}}
\subtitle{{{subtitle}}}
\author{{{author}}}
\date{{\today}}

\begin{{document}}

\begin{{frame}}[plain]
    \titlepage
\end{{frame}}

{slides_tex}

\end{{document}}
"""

        output_path = self.output_dir / f"{output_name}.tex"
        output_path.write_text(tex_code)
        return output_path

    def _build_slides(self, slides: List[Dict]) -> str:
        """Build slide content."""
        parts = []

        for slide in slides:
            title = slide.get("title", "")
            slide_type = slide.get("type", "content")
            content = slide.get("content", {})

            if slide_type == "bullets":
                items = content.get("items", [])
                items_tex = "\n".join([rf"    \item {item}" for item in items])
                parts.append(rf"""
\begin{{frame}}{{{title}}}
    \begin{{itemize}}
{items_tex}
    \end{{itemize}}
\end{{frame}}
""")
            elif slide_type == "stats":
                stats = content.get("stats", [])
                cols = []
                for stat in stats[:4]:
                    cols.append(rf"""
        \begin{{column}}{{0.25\textwidth}}
            \begin{{center}}
                \textcolor{{BrandPrimary}}{{\Huge {stat.get('value', '')}}}\\
                \small {stat.get('label', '')}
            \end{{center}}
        \end{{column}}""")
                parts.append(rf"""
\begin{{frame}}{{{title}}}
    \begin{{columns}}[T]
{"".join(cols)}
    \end{{columns}}
\end{{frame}}
""")
            else:
                text = content.get("text", "")
                parts.append(rf"""
\begin{{frame}}{{{title}}}
    {text}
\end{{frame}}
""")

        return "\n".join(parts)

    def compile_pdf(self, tex_path: Path) -> Optional[Path]:
        """
        Compile LaTeX to PDF.

        Returns:
            Path to PDF if successful, None otherwise.
        """
        try:
            result = subprocess.run(
                ["pdflatex", "-interaction=nonstopmode", tex_path.name],
                cwd=tex_path.parent,
                capture_output=True,
                timeout=60,
            )

            pdf_path = tex_path.with_suffix(".pdf")
            if pdf_path.exists():
                return pdf_path

            # Try xelatex as fallback
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", tex_path.name],
                cwd=tex_path.parent,
                capture_output=True,
                timeout=60,
            )

            if pdf_path.exists():
                return pdf_path

            return None

        except (subprocess.TimeoutExpired, FileNotFoundError):
            return None


# MCP Server implementation
async def handle_create_infographic(params: Dict) -> Dict:
    """Handle create_infographic tool call."""
    generator = LaTeXGenerator(params.get("output_path"))

    tex_path = generator.create_infographic(
        title=params["title"],
        infographic_type=params["type"],
        content=params["content"],
        subtitle=params.get("subtitle", ""),
    )

    result = {"tex_file": str(tex_path)}

    if params.get("compile_pdf", True):
        pdf_path = generator.compile_pdf(tex_path)
        if pdf_path:
            result["pdf_file"] = str(pdf_path)

    return result


async def handle_create_presentation(params: Dict) -> Dict:
    """Handle create_presentation tool call."""
    generator = LaTeXGenerator(params.get("output_path"))

    tex_path = generator.create_presentation(
        title=params["title"],
        slides=params["slides"],
        subtitle=params.get("subtitle", ""),
        author=params.get("author", "Dr. Shailesh"),
    )

    result = {"tex_file": str(tex_path)}

    if params.get("compile_pdf", True):
        pdf_path = generator.compile_pdf(tex_path)
        if pdf_path:
            result["pdf_file"] = str(pdf_path)

    return result


async def handle_compile_latex(params: Dict) -> Dict:
    """Handle compile_latex tool call."""
    tex_path = Path(params["tex_file"])
    generator = LaTeXGenerator(params.get("output_dir", str(tex_path.parent)))

    pdf_path = generator.compile_pdf(tex_path)

    if pdf_path:
        return {"success": True, "pdf_file": str(pdf_path)}
    else:
        return {"success": False, "error": "Compilation failed"}


if __name__ == "__main__":
    # Example usage
    generator = LaTeXGenerator("/tmp/latex-test")

    # Create a medical infographic
    tex_path = generator.create_infographic(
        title="Understanding Heart Health",
        subtitle="Your guide to cardiovascular wellness",
        infographic_type="medical",
        content={
            "stats": [
                {"icon": "heart", "value": "17.9M", "label": "Deaths/Year"},
                {"icon": "globe", "value": "32%", "label": "Global Deaths"},
                {"icon": "doctor", "value": "80%", "label": "Preventable"},
            ],
            "sections": [
                {
                    "title": "Risk Factors",
                    "items": ["High Blood Pressure", "High Cholesterol", "Smoking", "Obesity"]
                },
                {
                    "title": "Prevention",
                    "items": ["Regular Exercise", "Healthy Diet", "No Smoking", "Manage Stress"]
                }
            ],
            "alert": {
                "title": "Warning Signs",
                "items": ["Chest Pain", "Shortness of Breath", "Arm Pain", "Dizziness"]
            }
        }
    )

    print(f"Generated: {tex_path}")

    # Try to compile
    pdf_path = generator.compile_pdf(tex_path)
    if pdf_path:
        print(f"PDF: {pdf_path}")
    else:
        print("PDF compilation not available (LaTeX not installed)")
