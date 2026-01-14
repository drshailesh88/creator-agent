# LaTeX Graphics Generator

Generate high-quality infographics, presentations, and documents using LaTeX/TikZ with your brand colors.

## Why LaTeX?

- **Code-based**: AI excels at generating code, not pixel-perfect designs
- **Consistent**: Brand colors defined once, used everywhere
- **High-quality**: Vector graphics that scale perfectly
- **Reproducible**: Same code = same output every time

## Capabilities

### Infographics
- Medical/health infographics
- Statistics and data visualization
- Process flows and timelines
- Comparison charts
- Checklists and feature lists

### Presentations
- Beamer slides with brand theme
- Section dividers
- Stat cards and key takeaways

### Documents
- Articles with branded headers
- Info/warning/alert boxes
- Professional formatting

## Brand Colors (Auto-applied)

| Color | Use |
|-------|-----|
| Primary Teal (#16697A) | Titles, headers, CTAs |
| Secondary Teal (#218380) | Subtitles, panels |
| Accent Coral (#EF5350) | Highlights, callouts |
| Alert Red (#E74C3C) | Emergency info |
| Soft Aqua (#E8F5F4) | Backgrounds |
| Text Gray (#2F3E46) | Body text |

## Usage Examples

### Create an infographic
```
Create an infographic about heart health risks with:
- 4 key statistics at the top
- Risk factors with progress bars
- Prevention checklist
- Emergency warning box
```

### Create a presentation
```
Create a 5-slide presentation about cardiovascular health with:
- Title slide
- Key statistics
- Risk factors
- Prevention steps
- Conclusion with CTA
```

### Create a document
```
Create a patient guide about medication adherence with:
- Introduction section
- Step-by-step instructions
- Warning boxes for side effects
- Key takeaways box
```

## Output

The skill generates:
1. LaTeX source code (.tex file)
2. Compiled PDF (if LaTeX is available)

## Dependencies

- LaTeX distribution (TexLive recommended)
- TikZ package
- fontawesome5 package
- tcolorbox package (for documents)

## Installation

```bash
# Ubuntu/Debian
sudo apt-get install texlive-full

# macOS
brew install --cask mactex

# Or minimal install
sudo apt-get install texlive-latex-base texlive-fonts-recommended texlive-latex-extra
```
