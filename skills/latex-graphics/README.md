# LaTeX Graphics Skill

Generate high-quality, branded infographics, presentations, and documents using LaTeX/TikZ.

## Why LaTeX Instead of AI Image Generation?

| Approach | Pros | Cons |
|----------|------|------|
| **AI Image Gen (DALL-E, Midjourney)** | Creative, artistic | Inconsistent, can't edit, no brand control |
| **LaTeX/TikZ** | Consistent, editable, brand colors built-in | Less "creative", code-based |

**For infographics and data visualization, LaTeX wins** because:
- Same code = Same output every time
- Brand colors defined once, applied everywhere
- Vector graphics scale perfectly
- Easy to update content without redesigning

## Quick Start

### Generate an Infographic

```python
from skills.latex_graphics.generator import LaTeXGenerator

generator = LaTeXGenerator("/output/path")

tex_path = generator.create_infographic(
    title="Heart Health Guide",
    subtitle="Prevention and awareness",
    infographic_type="medical",
    content={
        "stats": [
            {"icon": "heart", "value": "17.9M", "label": "Deaths/Year"},
            {"icon": "globe", "value": "32%", "label": "Global Deaths"},
        ],
        "sections": [
            {"title": "Risk Factors", "items": ["High BP", "Cholesterol"]},
        ],
        "alert": {
            "title": "Warning Signs",
            "items": ["Chest Pain", "Shortness of Breath"]
        }
    }
)

# Compile to PDF
pdf_path = generator.compile_pdf(tex_path)
```

### Available Icons

Use these icon names in your content:

- `heart`, `heartbeat`, `brain`, `running`
- `chart`, `globe`, `user`, `doctor`
- `check`, `warning`, `info`, `lightbulb`
- `clock`, `calendar`, `pill`, `stethoscope`
- `ambulance`, `hospital`, `thermometer`

## Brand Colors

Your brand colors are automatically applied:

```
Primary Teal:    #16697A  (titles, headers)
Secondary Teal:  #218380  (subtitles, panels)
Accent Coral:    #EF5350  (highlights, CTAs)
Alert Red:       #E74C3C  (emergencies)
Background:      #E8F5F4  (soft aqua)
Text:            #2F3E46  (body copy)
```

## Templates

### Infographic Templates

Located in `latex/infographics/`:

- `base-template.tex` - Starting point with components
- `medical-infographic.tex` - Health/medical focused
- `components.sty` - Reusable TikZ components

### Presentation Templates

Located in `latex/presentations/`:

- `beamer-theme.sty` - Branded Beamer theme
- `sample-presentation.tex` - Example slides

### Document Templates

Located in `latex/documents/`:

- `article-template.tex` - Branded article/guide

## Requirements

Install LaTeX (one of these):

```bash
# Full installation (recommended)
sudo apt-get install texlive-full

# Minimal installation
sudo apt-get install texlive-latex-base texlive-fonts-recommended \
    texlive-latex-extra texlive-fonts-extra

# macOS
brew install --cask mactex
```

## File Structure

```
latex/
├── brand-colors.sty        # Brand color definitions
├── infographics/
│   ├── base-template.tex   # Base infographic template
│   ├── components.sty      # Reusable components
│   └── medical-infographic.tex
├── presentations/
│   ├── beamer-theme.sty    # Beamer theme
│   └── sample-presentation.tex
├── documents/
│   └── article-template.tex
└── examples/
    └── (generated outputs)

skills/latex-graphics/
├── SKILL.md               # Skill description
├── mcporter.json          # MCP tool definitions
├── generator.py           # Main generator code
└── README.md              # This file
```

## Tips

1. **Start with templates**: Copy and modify existing templates
2. **Use components**: The `components.sty` has pre-built elements
3. **Check compilation**: Run `pdflatex` to see errors
4. **Preview quickly**: Use online LaTeX editors to test

## Troubleshooting

**"Package not found"**: Install missing packages
```bash
sudo apt-get install texlive-fonts-extra
```

**"Font not found"**: Install fontawesome5
```bash
sudo apt-get install texlive-fonts-extra
```

**Compilation timeout**: Complex TikZ can be slow, increase timeout or simplify
