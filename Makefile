.PHONY: help tree check-structure docker-build docker-up docker-down docker-logs docker-ps docker-reset docker-config

DOCKER_COMPOSE = docker compose -f infra/docker/compose.yml

help:
	@echo "TradePilot AI — Development Makefile"
	@echo ""
	@echo "Repository status: Foundation stage — Docker environment configured."
	@echo ""
	@echo "Available commands:"
	@echo "  help              Show this help message"
	@echo "  tree              Display repository directory structure"
	@echo "  check-structure   Validate that all required paths exist"
	@echo ""
	@echo "Docker commands:"
	@echo "  docker-config     Show rendered Compose configuration"
	@echo "  docker-build      Build all container images"
	@echo "  docker-up         Start the development environment"
	@echo "  docker-down       Stop the environment (preserves volumes)"
	@echo "  docker-logs       Tail container logs"
	@echo "  docker-ps         List running containers"
	@echo "  docker-reset      Stop and remove all containers and volumes"

tree:
	@find . -maxdepth 4 -not -path './.git/*' -not -name '.DS_Store' | sort | sed 's|[^/]*/|  |g'

check-structure:
	@echo "Checking repository structure..."
	@ok=true; \
	for d in backend worker frontend infra/docker infra/deployment scripts tests/integration tests/fixtures docs storage/evidence; do \
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
	for obsolete in apps infrastructure packages/schemas packages/shared packages; do \
		if [ -e "$$obsolete" ]; then \
			echo "FAIL: obsolete path still exists: $$obsolete"; ok=false; \
		fi; \
	done; \
	$$ok && echo "PASS: All required paths exist. No obsolete paths remain." || exit 1

docker-config:
	$(DOCKER_COMPOSE) config

docker-build:
	$(DOCKER_COMPOSE) build

docker-up:
	$(DOCKER_COMPOSE) up -d

docker-down:
	$(DOCKER_COMPOSE) down

docker-logs:
	$(DOCKER_COMPOSE) logs -f

docker-ps:
	$(DOCKER_COMPOSE) ps

docker-reset:
	@echo "WARNING: This will remove all persistent data (PostgreSQL volumes, evidence storage)."
	@echo "Are you sure? Press Ctrl+C to abort, or wait 3 seconds..."
	@sleep 3
	$(DOCKER_COMPOSE) down -v
