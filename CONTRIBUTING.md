# Contributing

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (Python package manager)
- Python 3.14+

Install uv: <https://docs.astral.sh/uv/getting-started/installation/>

## Setup

```bash
git clone https://github.com/intentionally-left-nil/dfu.git
cd dfu
uv sync
```

This creates a `.venv` and installs the project plus dev/lint dependencies.

## Commands

Use the Makefile (or run the underlying `uv run` commands):

| Target | Description |
|--------|-------------|
| `make install` | Install tool locally via uv tool |
| `make sync` | Sync all dependencies (dev + lint groups) |
| `make sync-locked` | Sync from lockfile (CI) |
| `make sync-prod` | Sync production dependencies only |
| `make test` | Run pytest |
| `make lint` | Run ruff check |
| `make format` | Run ruff format (check only) |
| `make fix` | Run ruff check --fix and format |
| `make typing` | Run mypy |
| `make all` | Run lint, format, and typing (full check) |
| `make build` | Build wheel and sdist |
| `make run` | Run the dfu CLI |

Without make: e.g. `uv run pytest tests`, `uv run ruff check .`, `uv run dfu`.

## Before submitting

1. Run `make all` (or `make test` and `make lint` / `make format` / `make typing`).
2. Ensure pre-commit passes if you use it (`pre-commit run --all-files`).

## Pre-commit

Optional. To use pre-commit for format-on-commit:

```bash
pre-commit install
```

Hooks run ruff format. See `.pre-commit-config.yaml`.
