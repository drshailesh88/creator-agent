#!/bin/bash
# =============================================================================
# LaTeX Minimal Installation Script
# =============================================================================
# Installs only the essential TeX Live packages for the DrShailesh graphics system
# Optimized for VPS with limited disk space
#
# Usage: ./install-latex-minimal.sh [--dry-run]
#
# Disk space required: ~500MB
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Flags
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dry-run]"
            echo "  --dry-run    Show what would be installed without actually installing"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Detect OS
detect_os() {
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ -f /etc/alpine-release ]]; then
        echo "alpine"
    elif [[ -f /etc/debian_version ]]; then
        echo "debian"
    elif [[ -f /etc/redhat-release ]]; then
        echo "redhat"
    else
        echo "unknown"
    fi
}

# Check available disk space
check_disk_space() {
    local required_mb=$1
    local available_mb

    if [[ "$OSTYPE" == "darwin"* ]]; then
        available_mb=$(df -m / | awk 'NR==2 {print $4}')
    else
        available_mb=$(df -m / | awk 'NR==2 {print $4}')
    fi

    if [[ $available_mb -lt $required_mb ]]; then
        log_error "Insufficient disk space. Required: ${required_mb}MB, Available: ${available_mb}MB"
        exit 1
    fi

    log_info "Disk space check passed. Available: ${available_mb}MB, Required: ${required_mb}MB"
}

# Run command (respects dry-run)
run_cmd() {
    if [[ "$DRY_RUN" == true ]]; then
        log_info "[DRY-RUN] Would execute: $*"
    else
        "$@"
    fi
}

# Install on Debian/Ubuntu (minimal)
install_debian_minimal() {
    log_info "Installing minimal LaTeX on Debian/Ubuntu..."

    # Core packages only - minimal footprint
    local packages=(
        texlive-latex-base
        texlive-latex-recommended
        texlive-fonts-recommended
        texlive-pictures           # For TikZ
        texlive-latex-extra        # For tcolorbox, standalone
        latexmk
    )

    log_info "Updating package lists..."
    run_cmd sudo apt-get update

    log_info "Installing minimal packages: ${packages[*]}"
    run_cmd sudo apt-get install -y --no-install-recommends "${packages[@]}"

    # Install fontawesome5 via tlmgr if needed
    if ! kpsewhich fontawesome5.sty &> /dev/null; then
        log_info "Installing fontawesome5 via tlmgr..."
        if command -v tlmgr &> /dev/null; then
            run_cmd sudo tlmgr install fontawesome5 || {
                log_warning "tlmgr install failed, trying texlive-fonts-extra..."
                run_cmd sudo apt-get install -y texlive-fonts-extra
            }
        else
            log_warning "tlmgr not available, installing texlive-fonts-extra..."
            run_cmd sudo apt-get install -y texlive-fonts-extra
        fi
    fi

    log_success "Debian/Ubuntu minimal installation complete!"
}

# Install on Alpine Linux (minimal)
install_alpine_minimal() {
    log_info "Installing minimal LaTeX on Alpine Linux..."

    # Alpine packages are already relatively minimal
    local packages=(
        texlive
        texmf-dist-latexextra
        texmf-dist-pictures
    )

    log_info "Updating package lists..."
    run_cmd sudo apk update

    log_info "Installing minimal packages: ${packages[*]}"
    run_cmd sudo apk add --no-cache "${packages[@]}"

    log_success "Alpine minimal installation complete!"
}

# Install on macOS (minimal via BasicTeX)
install_macos_minimal() {
    log_info "Installing minimal LaTeX on macOS via BasicTeX..."

    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        log_warning "Homebrew not found. Installing Homebrew first..."
        if [[ "$DRY_RUN" == false ]]; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        else
            log_info "[DRY-RUN] Would install Homebrew"
        fi
    fi

    log_info "Installing BasicTeX (~100MB) instead of full MacTeX (~4GB)..."
    run_cmd brew install --cask basictex

    # Update PATH for current session
    if [[ "$DRY_RUN" == false ]]; then
        export PATH="/Library/TeX/texbin:$PATH"
        log_info "Added /Library/TeX/texbin to PATH"

        # Install required packages via tlmgr
        log_info "Installing required packages via tlmgr..."
        sudo tlmgr update --self

        local packages=(
            standalone
            tikz-cd
            pgfplots
            tcolorbox
            fontawesome5
            enumitem
            titlesec
            fancyhdr
            environ
            trimspaces
        )

        for pkg in "${packages[@]}"; do
            log_info "Installing: $pkg"
            sudo tlmgr install "$pkg" || log_warning "Failed to install: $pkg"
        done
    fi

    log_success "macOS minimal installation complete!"
    log_info "You may need to restart your terminal or add to your shell profile:"
    echo '  export PATH="/Library/TeX/texbin:$PATH"'
}

# Install additional packages via tlmgr
install_extra_packages() {
    log_info "Checking for tlmgr to install additional packages..."

    if ! command -v tlmgr &> /dev/null; then
        log_warning "tlmgr not found. Some packages may need manual installation."
        return 1
    fi

    # Required packages that may not be in base install
    local packages=(
        fontawesome5
        tcolorbox
        environ
        trimspaces
        etoolbox
        pgfplots
    )

    log_info "Installing additional packages via tlmgr..."
    for pkg in "${packages[@]}"; do
        if ! kpsewhich "$pkg.sty" &> /dev/null 2>&1; then
            log_info "Installing: $pkg"
            run_cmd sudo tlmgr install "$pkg" 2>/dev/null || log_warning "Could not install: $pkg"
        else
            log_success "Already installed: $pkg"
        fi
    done

    return 0
}

# Verify installation
verify_installation() {
    log_info "Verifying LaTeX installation..."

    local commands=(pdflatex latexmk kpsewhich)
    local missing=()

    for cmd in "${commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            local version=$($cmd --version 2>/dev/null | head -1 || echo "version unknown")
            log_success "Found: $cmd"
        else
            missing+=("$cmd")
        fi
    done

    if [[ ${#missing[@]} -gt 0 ]]; then
        log_warning "Missing commands: ${missing[*]}"
        return 1
    fi

    # Check for required packages
    log_info "Checking for required LaTeX packages..."

    local required_packages=(
        tikz
        xcolor
        standalone
    )

    local optional_packages=(
        fontawesome5
        tcolorbox
        beamer
    )

    local all_found=true

    for pkg in "${required_packages[@]}"; do
        if kpsewhich "$pkg.sty" &> /dev/null; then
            log_success "Required package found: $pkg"
        else
            log_error "Required package not found: $pkg"
            all_found=false
        fi
    done

    for pkg in "${optional_packages[@]}"; do
        if kpsewhich "$pkg.sty" &> /dev/null; then
            log_success "Optional package found: $pkg"
        else
            log_warning "Optional package not found: $pkg (some features may not work)"
        fi
    done

    if [[ "$all_found" == true ]]; then
        return 0
    else
        return 1
    fi
}

# Show disk space requirements
show_requirements() {
    echo ""
    echo "=============================================="
    echo "  LaTeX Minimal Installation - Requirements"
    echo "=============================================="
    echo ""
    echo "  Minimal TeX Live:   ~400-600 MB"
    echo "  BasicTeX (macOS):   ~100 MB + packages"
    echo ""
    echo "  Core packages installed:"
    echo "    - texlive-latex-base"
    echo "    - texlive-latex-recommended"
    echo "    - texlive-fonts-recommended"
    echo "    - texlive-pictures (TikZ)"
    echo "    - texlive-latex-extra"
    echo ""
    echo "  Note: Some features may require additional"
    echo "  packages installed via tlmgr"
    echo ""
    echo "=============================================="
    echo ""
}

# Main installation
main() {
    echo ""
    echo "=============================================="
    echo "  LaTeX Minimal Installation Script"
    echo "  DrShailesh Graphics System (VPS optimized)"
    echo "=============================================="
    echo ""

    if [[ "$DRY_RUN" == true ]]; then
        log_warning "Running in DRY-RUN mode - no changes will be made"
        echo ""
    fi

    # Detect OS
    local os=$(detect_os)
    log_info "Detected OS: $os"

    # Show requirements
    show_requirements

    # Check disk space (require 700MB to be safe)
    check_disk_space 700

    # Install based on OS
    case $os in
        debian)
            install_debian_minimal
            ;;
        alpine)
            install_alpine_minimal
            ;;
        macos)
            install_macos_minimal
            ;;
        redhat)
            log_warning "RedHat minimal install not optimized - using full install packages"
            log_info "For true minimal install, consider using TeX Live installer directly"
            # Fall through to basic install
            run_cmd sudo dnf install -y texlive texlive-latex latexmk || \
            run_cmd sudo yum install -y texlive texlive-latex latexmk
            install_extra_packages
            ;;
        *)
            log_error "Unsupported operating system: $os"
            log_info "Please install TeX Live manually from: https://www.tug.org/texlive/"
            log_info "Use the 'scheme-basic' or 'scheme-small' for minimal installation"
            exit 1
            ;;
    esac

    # Try to install extra packages
    install_extra_packages || true

    # Verify installation
    if [[ "$DRY_RUN" == false ]]; then
        echo ""
        if verify_installation; then
            echo ""
            log_success "LaTeX minimal installation complete!"
            log_info "Test your installation with:"
            echo "  cd $(dirname "$0")/../latex && make test"
        else
            echo ""
            log_warning "Installation completed with some missing packages"
            log_info "You may need to install additional packages via tlmgr:"
            echo "  sudo tlmgr install fontawesome5 tcolorbox"
        fi
    fi
}

# Run main
main "$@"
