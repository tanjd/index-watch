# Override for a different project name when reusing this Makefile
PROJECT_NAME ?= index-watch
DOCKER_IMAGE ?= tanjd/$(PROJECT_NAME):latest

.PHONY: help setup sync run test lint format typecheck check check-ci docker-build docker-run docker-push

.DEFAULT_GOAL := help

help:
	@echo "Index Watch — available targets:"
	@echo ""
	@echo "  make setup        Install deps and pre-commit hooks (uv sync, pre-commit install)"
	@echo "  make sync         Install dependencies (uv sync)"
	@echo "  make run         Run the bot (uv run python -m src.index)"
	@echo "  make test        Run tests (uv run pytest)"
	@echo "  make lint        Lint with Ruff (uv run ruff check .)"
	@echo "  make format      Format with Ruff (uv run ruff format .)"
	@echo "  make typecheck   Type-check with Basedpyright (uv run basedpyright src tests)"
	@echo "  make check       Lint, format, typecheck, and run tests"
	@echo "  make check-ci    Pre-commit (all files) then check — use in CI"
	@echo "  make docker-build  Build the Docker image"
	@echo "  make docker-run    Run the container (requires .env or pass BOT_TOKEN)"
	@echo "  make docker-push   Build, tag as $(DOCKER_IMAGE), and push to Docker Hub"

setup: sync
	uv run pre-commit install

sync:
	uv sync

run:
	PYTHONUNBUFFERED=1 uv run python -m src.index

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run basedpyright src tests

check: lint format typecheck test

check-ci:
	uv run pre-commit run --all-files
	$(MAKE) check

docker-build:
	@command -v docker >/dev/null 2>&1 || { echo "Docker not found. Run this from a host terminal (WSL2 or PowerShell) where Docker is installed, or add the Docker feature to the devcontainer (see README)."; exit 127; }
	docker build -t $(PROJECT_NAME) .

docker-run:
	@command -v docker >/dev/null 2>&1 || { echo "Docker not found. Run this from a host terminal (WSL2 or PowerShell) where Docker is installed, or add the Docker feature to the devcontainer (see README)."; exit 127; }
	docker run --rm -it --env-file .env -p 9999:9999 --name $(PROJECT_NAME) $(PROJECT_NAME)

docker-push: docker-build
	@command -v docker >/dev/null 2>&1 || { echo "Docker not found."; exit 127; }
	docker tag $(PROJECT_NAME):latest $(DOCKER_IMAGE)
	docker push $(DOCKER_IMAGE)
