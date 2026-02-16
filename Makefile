# Override for a different project name when reusing this Makefile
PROJECT_NAME ?= index-watch
DOCKER_IMAGE ?= tanjd/$(PROJECT_NAME):latest

# Suppress "Entering/Leaving directory" messages
MAKEFLAGS += --no-print-directory

.PHONY: help setup sync upgrade run test lint format typecheck check check-ci docker-build docker-run docker-push

.DEFAULT_GOAL := help

help: ## Show this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(PROJECT_NAME) — Available Commands:\n\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) }' $(MAKEFILE_LIST)

##@ Development

setup: sync ## Install deps and pre-commit hooks
	uv run pre-commit install

sync: ## Install dependencies with uv
	uv sync

upgrade: ## Upgrade dependencies (uv lock --upgrade)
	uv lock --upgrade

run: ## Run the bot locally
	PYTHONUNBUFFERED=1 uv run python -m index_watch

##@ Testing & Quality

test: ## Run tests with pytest
	uv run pytest

lint: ## Lint code with Ruff
	uv run ruff check .

format: ## Format code with Ruff
	uv run ruff format .

typecheck: ## Type-check with Basedpyright
	uv run basedpyright src tests

check: lint format typecheck test ## Run all checks (lint, format, typecheck, test)

check-ci: ## Run pre-commit and all checks (for CI)
	uv run pre-commit run --all-files
	$(MAKE) check

##@ Docker

docker-build: ## Build Docker image
	docker build -t $(PROJECT_NAME) .

docker-run: ## Run Docker container with .env file
	docker run --rm -it --env-file .env -p 9999:9999 --name $(PROJECT_NAME) $(PROJECT_NAME)

docker-push: docker-build ## Build, tag, and push to Docker Hub
	docker tag $(PROJECT_NAME):latest $(DOCKER_IMAGE)
	docker push $(DOCKER_IMAGE)
