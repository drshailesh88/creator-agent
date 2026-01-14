#!/bin/bash
# =============================================================================
# LaTeX Full Installation Script
# =============================================================================
# Installs TeX Live with all packages required for the DrShailesh graphics system
# Supports: Ubuntu/Debian, Alpine Linux, macOS
#
# Usage: ./install-latex.sh [--dry-run]
#
# Disk space required: ~2GB for full installation
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

# Install on Debian/Ubuntu
install_debian() {
    log_info "Installing LaTeX on Debian/Ubuntu..."

    local packages=(
        texlive-latex-base
        texlive-latex-recommended
        texlive-latex-extra
        texlive-fonts-recommended
        texlive-fonts-extra
        texlive-pictures
        texlive-science
        texlive-xetex
        latexmk
    )

    log_info "Updating package lists..."
    run_cmd sudo apt-get update

    log_info "Installing packages: ${packages[*]}"
    run_cmd sudo apt-get install -y "${packages[@]}"

    log_success "Debian/Ubuntu installation complete!"
}

# Install on Alpine Linux
install_alpine() {
    log_info "Installing LaTeX on Alpine Linux..."

    local packages=(
        texlive
        texlive-full
        texmf-dist-latexextra
        texmf-dist-fontsextra
        texmf-dist-pictures
    )

    log_info "Updating package lists..."
    run_cmd sudo apk update

    log_info "Installing packages: ${packages[*]}"
    run_cmd sudo apk add --no-cache "${packages[@]}"

    log_success "Alpine installation complete!"
}

# Install on macOS
install_macos() {
    log_info "Installing LaTeX on macOS..."

    # Check for Homebrew
    if ! command -v brew &> /dev/null; then
        log_warning "Homebrew not found. Installing Homebrew first..."
        if [[ "$DRY_RUN" == false ]]; then
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        else
            log_info "[DRY-RUN] Would install Homebrew"
        fi
    fi

    log_info "Installing MacTeX via Homebrew Cask..."
    log_warning "This will download ~4GB and install the full MacTeX distribution"

    run_cmd brew install --cask mactex

    # Update PATH for current session
    if [[ "$DRY_RUN" == false ]]; then
        export PATH="/Library/TeX/texbin:$PATH"
        log_info "Added /Library/TeX/texbin to PATH"
    fi

    log_success "macOS installation complete!"
    log_info "You may need to restart your terminal or add to your shell profile:"
    echo '  export PATH="/Library/TeX/texbin:$PATH"'
}

# Install on RedHat/CentOS/Fedora
install_redhat() {
    log_info "Installing LaTeX on RedHat/CentOS/Fedora..."

    local packages=(
        texlive
        texlive-latex
        texlive-collection-latexextra
        texlive-collection-fontsextra
        texlive-xetex
        latexmk
    )

    if command -v dnf &> /dev/null; then
        run_cmd sudo dnf install -y "${packages[@]}"
    else
        run_cmd sudo yum install -y "${packages[@]}"
    fi

    log_success "RedHat/CentOS/Fedora installation complete!"
}

# Verify installation
verify_installation() {
    log_info "Verifying LaTeX installation..."

    local commands=(pdflatex xelatex latexmk kpsewhich)
    local missing=()

    for cmd in "${commands[@]}"; do
        if command -v "$cmd" &> /dev/null; then
            local version=$($cmd --version 2>/dev/null | head -1 || echo "version unknown")
            log_success "Found: $cmd - $version"
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

    local packages=(
        tikz
        fontawesome5
        xcolor
        tcolorbox
        beamer
        standalone
    )

    for pkg in "${packages[@]}"; do
        if kpsewhich "$pkg.sty" &> /dev/null; then
            log_success "Package found: $pkg"
        else
            log_warning "Package not found: $pkg (may need tlmgr install)"
        fi
    done

    return 0
}

# Show disk space requirements
show_requirements() {
    echo ""
    echo "=============================================="
    echo "  LaTeX Full Installation - Disk Requirements"
    echo "=============================================="
    echo ""
    echo "  Full TeX Live:      ~2-4 GB"
    echo "  After installation: ~2.5 GB used"
    echo ""
    echo "  Required packages:"
    echo "    - texlive-latex-base"
    echo "    - texlive-latex-recommended"
    echo "    - texlive-latex-extra"
    echo "    - texlive-fonts-recommended"
    echo "    - texlive-fonts-extra (for fontawesome5)"
    echo "    - texlive-pictures (for TikZ)"
    echo "    - texlive-science"
    echo "    - texlive-xetex"
    echo ""
    echo "=============================================="
    echo ""
}

# Main installation
main() {
    echo ""
    echo "=============================================="
    echo "  LaTeX Full Installation Script"
    echo "  DrShailesh Graphics System"
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

    # Check disk space (require 3GB to be safe)
    check_disk_space 3000

    # Install based on OS
    case $os in
        debian)
            install_debian
            ;;
        alpine)
            install_alpine
            ;;
        macos)
            install_macos
            ;;
        redhat)
            install_redhat
            ;;
        *)
            log_error "Unsupported operating system: $os"
            log_info "Please install TeX Live manually from: https://www.tug.org/texlive/"
            exit 1
            ;;
    esac

    # Verify installation
    if [[ "$DRY_RUN" == false ]]; then
        echo ""
        verify_installation

        echo ""
        log_success "LaTeX installation complete!"
        log_info "Test your installation with:"
        echo "  cd $(dirname "$0")/../latex && make test"
    fi
}

# Run main
main "$@"
