# =============================================================================
# LaTeX Build Automation - DrShailesh Graphics System
# =============================================================================
#
# Usage:
#   make all          - Compile all templates
#   make test         - Run installation test
#   make infographics - Compile infographic templates
#   make presentations - Compile presentation templates
#   make documents    - Compile document templates
#   make clean        - Remove build artifacts
#   make watch FILE=path/to/file.tex - Watch and recompile on changes
#
# =============================================================================

# Configuration
LATEX = pdflatex
LATEXMK = latexmk
LATEXFLAGS = -interaction=nonstopmode -file-line-error -halt-on-error
LATEXMK_FLAGS = -pdf -interaction=nonstopmode -file-line-error

# Directories
SRCDIR = .
OUTDIR = output
INFOGRAPHICS_DIR = infographics
PRESENTATIONS_DIR = presentations
DOCUMENTS_DIR = documents

# Source files
INFOGRAPHIC_SRCS = $(wildcard $(INFOGRAPHICS_DIR)/*.tex)
PRESENTATION_SRCS = $(wildcard $(PRESENTATIONS_DIR)/*.tex)
DOCUMENT_SRCS = $(wildcard $(DOCUMENTS_DIR)/*.tex)

# Output files
INFOGRAPHIC_PDFS = $(patsubst $(INFOGRAPHICS_DIR)/%.tex,$(OUTDIR)/infographics/%.pdf,$(INFOGRAPHIC_SRCS))
PRESENTATION_PDFS = $(patsubst $(PRESENTATIONS_DIR)/%.tex,$(OUTDIR)/presentations/%.pdf,$(PRESENTATION_SRCS))
DOCUMENT_PDFS = $(patsubst $(DOCUMENTS_DIR)/%.tex,$(OUTDIR)/documents/%.pdf,$(DOCUMENT_SRCS))

# Set TEXINPUTS to include current directory and subdirectories
export TEXINPUTS := .:.//:$(SRCDIR)//:

# Colors for terminal output
CYAN = \033[0;36m
GREEN = \033[0;32m
YELLOW = \033[1;33m
RED = \033[0;31m
NC = \033[0m # No Color

# =============================================================================
# PHONY TARGETS
# =============================================================================

.PHONY: all test infographics presentations documents clean clean-all help watch verify-deps

# Default target
all: verify-deps $(OUTDIR) infographics presentations documents
	@echo "$(GREEN)[SUCCESS]$(NC) All templates compiled successfully!"
	@echo "$(CYAN)[INFO]$(NC) Output files are in $(OUTDIR)/"

# =============================================================================
# DEPENDENCY VERIFICATION
# =============================================================================

verify-deps:
	@echo "$(CYAN)[INFO]$(NC) Verifying LaTeX installation..."
	@which $(LATEX) > /dev/null 2>&1 || (echo "$(RED)[ERROR]$(NC) pdflatex not found. Run ./scripts/install-latex.sh" && exit 1)
	@echo "$(GREEN)[OK]$(NC) pdflatex found"

# =============================================================================
# TEST TARGET
# =============================================================================

test: verify-deps $(OUTDIR)
	@echo "$(CYAN)[INFO]$(NC) Running installation test..."
	@cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) -output-directory=$(OUTDIR) test-installation.tex > /dev/null 2>&1 && \
		echo "$(GREEN)[SUCCESS]$(NC) Test passed! See $(OUTDIR)/test-installation.pdf" || \
		(echo "$(RED)[FAILED]$(NC) Test compilation failed. Check LaTeX installation." && \
		cd $(SRCDIR) && $(LATEX) -output-directory=$(OUTDIR) test-installation.tex && exit 1)

# =============================================================================
# OUTPUT DIRECTORIES
# =============================================================================

$(OUTDIR):
	@mkdir -p $(OUTDIR)/infographics
	@mkdir -p $(OUTDIR)/presentations
	@mkdir -p $(OUTDIR)/documents

# =============================================================================
# INFOGRAPHICS
# =============================================================================

infographics: verify-deps $(OUTDIR) $(INFOGRAPHIC_PDFS)
	@echo "$(GREEN)[SUCCESS]$(NC) Infographics compiled"

$(OUTDIR)/infographics/%.pdf: $(INFOGRAPHICS_DIR)/%.tex brand-colors.sty $(INFOGRAPHICS_DIR)/components.sty
	@echo "$(CYAN)[COMPILE]$(NC) $<"
	@cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) -output-directory=$(OUTDIR)/infographics $< > /dev/null 2>&1 || \
		(echo "$(RED)[ERROR]$(NC) Failed to compile $<" && $(LATEX) -output-directory=$(OUTDIR)/infographics $<)
	@echo "$(GREEN)[OK]$(NC) $@"

# =============================================================================
# PRESENTATIONS
# =============================================================================

presentations: verify-deps $(OUTDIR) $(PRESENTATION_PDFS)
	@echo "$(GREEN)[SUCCESS]$(NC) Presentations compiled"

$(OUTDIR)/presentations/%.pdf: $(PRESENTATIONS_DIR)/%.tex brand-colors.sty $(PRESENTATIONS_DIR)/beamer-theme.sty
	@echo "$(CYAN)[COMPILE]$(NC) $<"
	@cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) -output-directory=$(OUTDIR)/presentations $< > /dev/null 2>&1 || \
		(echo "$(RED)[ERROR]$(NC) Failed to compile $<" && $(LATEX) -output-directory=$(OUTDIR)/presentations $<)
	@# Run twice for TOC/references
	@cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) -output-directory=$(OUTDIR)/presentations $< > /dev/null 2>&1
	@echo "$(GREEN)[OK]$(NC) $@"

# =============================================================================
# DOCUMENTS
# =============================================================================

documents: verify-deps $(OUTDIR) $(DOCUMENT_PDFS)
	@echo "$(GREEN)[SUCCESS]$(NC) Documents compiled"

$(OUTDIR)/documents/%.pdf: $(DOCUMENTS_DIR)/%.tex brand-colors.sty
	@echo "$(CYAN)[COMPILE]$(NC) $<"
	@cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) -output-directory=$(OUTDIR)/documents $< > /dev/null 2>&1 || \
		(echo "$(RED)[ERROR]$(NC) Failed to compile $<" && $(LATEX) -output-directory=$(OUTDIR)/documents $<)
	@# Run twice for TOC/references
	@cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) -output-directory=$(OUTDIR)/documents $< > /dev/null 2>&1
	@echo "$(GREEN)[OK]$(NC) $@"

# =============================================================================
# SINGLE FILE COMPILATION
# =============================================================================

# Compile a single file: make single FILE=path/to/file.tex
single: verify-deps $(OUTDIR)
ifndef FILE
	@echo "$(RED)[ERROR]$(NC) No FILE specified. Usage: make single FILE=path/to/file.tex"
	@exit 1
endif
	@echo "$(CYAN)[COMPILE]$(NC) $(FILE)"
	@cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) -output-directory=$(OUTDIR) $(FILE)
	@echo "$(GREEN)[SUCCESS]$(NC) Compiled $(FILE)"

# =============================================================================
# WATCH MODE
# =============================================================================

# Watch a file and recompile on changes
# Usage: make watch FILE=infographics/base-template.tex
watch: verify-deps
ifndef FILE
	@echo "$(RED)[ERROR]$(NC) No FILE specified. Usage: make watch FILE=path/to/file.tex"
	@exit 1
endif
	@echo "$(CYAN)[WATCH]$(NC) Watching $(FILE) for changes..."
	@echo "$(YELLOW)[INFO]$(NC) Press Ctrl+C to stop"
	@if command -v latexmk > /dev/null 2>&1; then \
		cd $(SRCDIR) && $(LATEXMK) -pvc $(LATEXMK_FLAGS) $(FILE); \
	elif command -v inotifywait > /dev/null 2>&1; then \
		while true; do \
			inotifywait -q -e modify $(FILE) $(SRCDIR)/*.sty; \
			echo "$(CYAN)[RECOMPILE]$(NC) $(FILE)"; \
			cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) $(FILE) || true; \
		done; \
	elif command -v fswatch > /dev/null 2>&1; then \
		fswatch -o $(FILE) $(SRCDIR)/*.sty | while read; do \
			echo "$(CYAN)[RECOMPILE]$(NC) $(FILE)"; \
			cd $(SRCDIR) && $(LATEX) $(LATEXFLAGS) $(FILE) || true; \
		done; \
	else \
		echo "$(RED)[ERROR]$(NC) No watch tool available. Install latexmk, inotifywait, or fswatch"; \
		exit 1; \
	fi

# =============================================================================
# CLEAN TARGETS
# =============================================================================

clean:
	@echo "$(CYAN)[CLEAN]$(NC) Removing build artifacts..."
	@rm -f $(OUTDIR)/*.aux $(OUTDIR)/*.log $(OUTDIR)/*.out $(OUTDIR)/*.toc
	@rm -f $(OUTDIR)/*.nav $(OUTDIR)/*.snm $(OUTDIR)/*.vrb
	@rm -f $(OUTDIR)/**/*.aux $(OUTDIR)/**/*.log $(OUTDIR)/**/*.out $(OUTDIR)/**/*.toc
	@rm -f $(OUTDIR)/**/*.nav $(OUTDIR)/**/*.snm $(OUTDIR)/**/*.vrb
	@rm -f *.aux *.log *.out *.toc *.nav *.snm *.vrb *.fls *.fdb_latexmk *.synctex.gz
	@rm -f $(INFOGRAPHICS_DIR)/*.aux $(INFOGRAPHICS_DIR)/*.log $(INFOGRAPHICS_DIR)/*.out
	@rm -f $(PRESENTATIONS_DIR)/*.aux $(PRESENTATIONS_DIR)/*.log $(PRESENTATIONS_DIR)/*.out
	@rm -f $(DOCUMENTS_DIR)/*.aux $(DOCUMENTS_DIR)/*.log $(DOCUMENTS_DIR)/*.out
	@echo "$(GREEN)[OK]$(NC) Build artifacts removed"

clean-all: clean
	@echo "$(CYAN)[CLEAN]$(NC) Removing all output files..."
	@rm -rf $(OUTDIR)
	@echo "$(GREEN)[OK]$(NC) Output directory removed"

# =============================================================================
# HELP
# =============================================================================

help:
	@echo ""
	@echo "$(CYAN)LaTeX Build System - DrShailesh Graphics$(NC)"
	@echo "=========================================="
	@echo ""
	@echo "$(YELLOW)Targets:$(NC)"
	@echo "  make all           - Compile all templates"
	@echo "  make test          - Run installation test"
	@echo "  make infographics  - Compile infographic templates"
	@echo "  make presentations - Compile presentation templates"
	@echo "  make documents     - Compile document templates"
	@echo "  make single FILE=x - Compile a single file"
	@echo "  make watch FILE=x  - Watch file and recompile on changes"
	@echo "  make clean         - Remove build artifacts (keep PDFs)"
	@echo "  make clean-all     - Remove all output including PDFs"
	@echo "  make help          - Show this help message"
	@echo ""
	@echo "$(YELLOW)Examples:$(NC)"
	@echo "  make test"
	@echo "  make single FILE=infographics/medical-infographic.tex"
	@echo "  make watch FILE=documents/article-template.tex"
	@echo ""
	@echo "$(YELLOW)Output:$(NC)"
	@echo "  Compiled PDFs are placed in: $(OUTDIR)/"
	@echo ""
