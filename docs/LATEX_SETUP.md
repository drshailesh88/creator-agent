# LaTeX Setup Guide

This guide covers installing and configuring LaTeX for the DrShailesh graphics system, which uses TikZ for creating infographics, presentations, and branded documents.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation Options](#installation-options)
- [Full Installation](#full-installation)
- [Minimal Installation (VPS)](#minimal-installation-vps)
- [Manual Installation](#manual-installation)
- [Testing Your Installation](#testing-your-installation)
- [Compiling Templates](#compiling-templates)
- [Troubleshooting](#troubleshooting)
- [Package Reference](#package-reference)

---

## Prerequisites

Before installing LaTeX, ensure you have:

- **Disk Space**:
  - Full installation: ~2-4 GB
  - Minimal installation: ~500 MB
- **RAM**: At least 1 GB free during compilation
- **Permissions**: sudo/admin access for system-wide installation

### Operating System Support

| OS | Full Install | Minimal Install | Notes |
|----|--------------|-----------------|-------|
| Ubuntu/Debian | Yes | Yes | Recommended |
| Alpine Linux | Yes | Yes | Good for containers |
| macOS | Yes | Yes | Uses Homebrew |
| RHEL/CentOS/Fedora | Yes | Partial | Full install recommended |
| Windows | Manual | Manual | Use MiKTeX or TeX Live |

---

## Installation Options

We provide two installation scripts:

### Full Installation (~2 GB)

Best for development machines with plenty of disk space. Includes all fonts, extra packages, and XeLaTeX support.

```bash
cd /home/user/creator-agent
./scripts/install-latex.sh
```

### Minimal Installation (~500 MB)

Optimized for VPS and servers with limited disk space. Includes only essential packages.

```bash
cd /home/user/creator-agent
./scripts/install-latex-minimal.sh
```

### Dry Run Mode

Preview what will be installed without making changes:

```bash
./scripts/install-latex.sh --dry-run
./scripts/install-latex-minimal.sh --dry-run
```

---

## Full Installation

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-latex-extra \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-pictures \
    texlive-science \
    texlive-xetex \
    latexmk
```

### macOS

Using Homebrew:

```bash
brew install --cask mactex
```

After installation, add to your shell profile:

```bash
export PATH="/Library/TeX/texbin:$PATH"
```

### Alpine Linux

```bash
apk add texlive texlive-full texmf-dist-latexextra texmf-dist-fontsextra
```

---

## Minimal Installation (VPS)

For servers with limited disk space, install only essential packages:

### Ubuntu/Debian

```bash
sudo apt-get update
sudo apt-get install -y --no-install-recommends \
    texlive-latex-base \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-pictures \
    texlive-latex-extra \
    latexmk

# Install fontawesome5 separately if needed
sudo apt-get install -y texlive-fonts-extra
# OR via tlmgr:
sudo tlmgr install fontawesome5
```

### macOS (BasicTeX)

```bash
brew install --cask basictex
export PATH="/Library/TeX/texbin:$PATH"

# Install required packages
sudo tlmgr update --self
sudo tlmgr install standalone tcolorbox fontawesome5 enumitem titlesec fancyhdr
```

---

## Manual Installation

If automatic scripts do not work, install TeX Live manually:

1. Download from: https://www.tug.org/texlive/
2. Run the installer
3. Choose scheme:
   - `scheme-full` for full installation
   - `scheme-basic` or `scheme-small` for minimal
4. Install additional packages via tlmgr:

```bash
tlmgr install tikz fontawesome5 tcolorbox standalone beamer
```

---

## Testing Your Installation

### Quick Test

```bash
cd /home/user/creator-agent/latex
make test
```

### Manual Test

```bash
cd /home/user/creator-agent/latex
pdflatex test-installation.tex
```

If successful, you will see `test-installation.pdf` created.

### Verify Required Commands

```bash
which pdflatex    # Should show path
which latexmk     # Should show path
kpsewhich tikz.sty        # Should show path
kpsewhich fontawesome5.sty # Should show path
```

---

## Compiling Templates

### Using Make (Recommended)

```bash
cd /home/user/creator-agent/latex

# Compile all templates
make all

# Compile specific types
make infographics
make presentations
make documents

# Clean build artifacts
make clean

# Watch mode (auto-recompile on changes)
make watch FILE=infographics/base-template.tex
```

### Manual Compilation

```bash
# Using pdflatex (standard)
pdflatex -output-directory=output document.tex
pdflatex -output-directory=output document.tex  # Run twice for references

# Using latexmk (recommended - handles dependencies)
latexmk -pdf -output-directory=output document.tex

# Using XeLaTeX (for advanced font support)
xelatex -output-directory=output document.tex
```

### Output Location

Compiled PDFs are placed in:
- `latex/output/` - Main output directory
- Or same directory as source if output dir not specified

---

## Troubleshooting

### Common Issues

#### 1. "fontawesome5.sty not found"

**Cause**: fontawesome5 package not installed.

**Solution**:
```bash
# Debian/Ubuntu
sudo apt-get install texlive-fonts-extra

# Or via tlmgr
sudo tlmgr install fontawesome5
```

#### 2. "tikz.sty not found"

**Cause**: TikZ/PGF package not installed.

**Solution**:
```bash
# Debian/Ubuntu
sudo apt-get install texlive-pictures

# Or via tlmgr
sudo tlmgr install pgf
```

#### 3. "tcolorbox.sty not found"

**Cause**: tcolorbox package not installed.

**Solution**:
```bash
# Debian/Ubuntu
sudo apt-get install texlive-latex-extra

# Or via tlmgr
sudo tlmgr install tcolorbox environ trimspaces etoolbox
```

#### 4. "brand-colors.sty not found"

**Cause**: Custom style file not in LaTeX path.

**Solution**:
Ensure you compile from the `latex/` directory or add to TEXINPUTS:
```bash
export TEXINPUTS="./:/home/user/creator-agent/latex//:"
```

Or copy `brand-colors.sty` to the same directory as your `.tex` file.

#### 5. "Dimension too large" errors

**Cause**: TikZ calculations producing invalid dimensions.

**Solution**:
- Check for typos in coordinates
- Ensure all measurements use consistent units
- Reduce complex calculations

#### 6. "I can't find file `pgfsys-pdftex.def`"

**Cause**: PGF driver files missing.

**Solution**:
```bash
sudo tlmgr install pgf
```

#### 7. Slow compilation

**Cause**: Large documents or many TikZ graphics.

**Solutions**:
- Use `latexmk` for smart recompilation
- Enable external TikZ library for caching
- Use `standalone` class for individual graphics

### Debug Mode

For detailed error messages:

```bash
pdflatex -interaction=nonstopmode -file-line-error document.tex
```

### Check Package Installation

```bash
# Check if package exists
kpsewhich packagename.sty

# List installed packages
tlmgr list --only-installed

# Search for package
tlmgr search packagename
```

---

## Package Reference

### Required Packages

| Package | Purpose | Installation |
|---------|---------|--------------|
| tikz | Graphics and diagrams | texlive-pictures |
| xcolor | Color definitions | texlive-latex-recommended |
| fontawesome5 | Icons | texlive-fonts-extra |
| tcolorbox | Colored boxes | texlive-latex-extra |
| standalone | Single-graphic documents | texlive-latex-extra |
| beamer | Presentations | texlive-latex-recommended |

### Optional Packages

| Package | Purpose | Installation |
|---------|---------|--------------|
| pgfplots | Data visualization | texlive-pictures |
| hyperref | PDF links | texlive-latex-base |
| geometry | Page layout | texlive-latex-base |
| fancyhdr | Headers/footers | texlive-latex-base |

### TikZ Libraries Used

Our templates use these TikZ libraries:
- shapes.geometric
- shapes.symbols
- arrows.meta
- positioning
- calc
- fit
- backgrounds
- shadows.blur
- decorations.pathreplacing
- patterns

---

## Directory Structure

```
latex/
├── brand-colors.sty          # Brand color definitions
├── Makefile                   # Build automation
├── test-installation.tex      # Installation test file
├── output/                    # Compiled PDFs (gitignored)
├── infographics/
│   ├── components.sty         # Reusable TikZ components
│   ├── base-template.tex      # Base infographic template
│   └── medical-infographic.tex
├── presentations/
│   ├── beamer-theme.sty       # Beamer theme
│   └── sample-presentation.tex
└── documents/
    └── article-template.tex   # Document template
```

---

## Getting Help

- TeX Live Documentation: https://www.tug.org/texlive/doc.html
- TikZ/PGF Manual: https://tikz.dev/
- LaTeX Stack Exchange: https://tex.stackexchange.com/
- Overleaf Documentation: https://www.overleaf.com/learn

---

## Version Information

- Tested with TeX Live 2023, 2024
- Minimum TeX Live version: 2020
- pdfTeX version: 3.14159265 or later
