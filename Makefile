.PHONY: install sync sync-locked sync-prod test lint format fix typing all build run help

install:
	uv tool install --editable .

sync:
	uv sync

sync-locked:
	uv sync --locked

sync-prod:
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
	@echo "install        - install tool locally via uv tool"
	@echo "sync           - sync dev + lint deps"
	@echo "sync-locked    - sync from lockfile (CI)"
	@echo "sync-prod      - sync production deps only"
	@echo "test           - run pytest"
	@echo "lint           - ruff check"
	@echo "format         - ruff format (check only)"
	@echo "fix            - ruff check --fix and format"
	@echo "typing         - mypy"
	@echo "all            - lint + format + typing"
	@echo "build          - build wheel and sdist"
	@echo "run            - run dfu CLI"
