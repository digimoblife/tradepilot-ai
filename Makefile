.PHONY: help tree check-structure

help:
	@echo "TradePilot AI — Development Makefile"
	@echo ""
	@echo "Repository status: Foundation stage — no services configured yet."
	@echo ""
	@echo "Available commands:"
	@echo "  help              Show this help message"
	@echo "  tree              Display repository directory structure"
	@echo "  check-structure   Validate that all required paths exist"

tree:
	@find . -maxdepth 4 -not -path './.git/*' -not -name '.DS_Store' | sort | sed 's|[^/]*/|  |g'

check-structure:
	@echo "Checking repository structure..."
	@ok=true; \
	for d in apps/api apps/worker apps/web packages/schemas packages/shared infrastructure/docker infrastructure/deployment scripts tests/integration tests/fixtures docs storage/evidence; do \
		if [ ! -d "$$d" ]; then \
			echo "FAIL: $$d missing"; ok=false; \
		fi; \
	done; \
	for f in .editorconfig .env.example .gitignore README.md; do \
		if [ ! -f "$$f" ]; then \
			echo "FAIL: $$f missing"; ok=false; \
		fi; \
	done; \
	if [ ! -f "storage/evidence/.gitkeep" ]; then \
		echo "FAIL: storage/evidence/.gitkeep missing"; ok=false; \
	fi; \
	$$ok && echo "PASS: All required paths exist." || exit 1
