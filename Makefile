.PHONY: install install-locked install-prod test lint format fix typing all build run help

install:
	uv sync

install-locked:
	uv sync --locked

install-prod:
	uv sync --no-dev --no-group lint

test:
	uv run pytest tests

lint:
	uv run ruff check .

format:
	uv run ruff format --check .

fix:
	uv run ruff check --fix . && uv run ruff format .

typing:
	uv run mypy --install-types --non-interactive dfu tests

all: lint format typing

build:
	uv build

run:
	uv run dfu

help:
	@echo "install        - sync dev + lint deps (default)"
	@echo "install-locked - sync from lockfile (CI)"
	@echo "install-prod   - sync production deps only"
	@echo "test         - run pytest"
	@echo "lint         - ruff check"
	@echo "format       - ruff format (check only)"
	@echo "fix          - ruff check --fix and format"
	@echo "typing       - mypy"
	@echo "all          - lint + format + typing"
	@echo "build        - build wheel and sdist"
	@echo "run          - run dfu CLI"
