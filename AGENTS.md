# AGENTS.md — Guidance for AI Coding Agents

## What is dfu?

dfu (don't forget updates) is a CLI tool that creates installable packages from btrfs snapshot diffs. The idea is: you take a "before" snapshot of your system, make changes (install software, edit config files, tweak settings), then take an "after" snapshot. dfu computes what changed between the two snapshots and stores the result as a portable, replayable package. Later, you (or someone else) can apply that package to reproduce those changes on another system, or reverse it to uninstall.

### How the diff process works

The diff engine uses git internally to produce patches. When generating a diff:

1. A temporary git repo (the "playground") is created and initialized with a `.gitignore`. The `.gitignore` filters out noise — binaries in `/usr/bin`, libraries in `/usr/lib`, cache files, etc. The user can customize this `.gitignore` in their package directory.
2. The "before" versions of all changed files (from the pre-snapshot btrfs mount) are copied into the playground under a `files/` directory and committed as "Initial files". File permissions (mode, uid, gid) are recorded separately in `acl.txt` using a simple `path mode uid gid` text format.
3. The "after" versions are copied in and committed as "Modified files", along with updated `acl.txt` and a `config.json` with the pack format version.
4. A `.patch` file (the text output of `git diff` between the two commits) and a `.pack` file (a `git bundle` containing the full history) are written into the package directory. The naming convention is `{from_index:03}_to_{to_index:03}.patch/.pack`.

### How apply works

Applying a package also uses a temporary git playground:

1. The current filesystem versions of files referenced in the patch are copied into a fresh playground and committed.
2. The `.patch` is applied using `git apply --3way`, which enables three-way merge. If there are conflicts (the target system's files differ from what the patch expects), the user gets dropped into a subshell to resolve them manually.
3. File ownership and permissions are restored from the embedded `acl.txt`.
4. The resolved files are copied back to the real filesystem (via sudo).

Applying supports reversal (applies the patch in reverse to uninstall) and an interactive rebase-like pick/edit/drop UI over patch steps.

### Key subsystems

- **`dfu/snapshots/`** — snapper integration, btrfs subvolume mounting, snapshot diffing. `snapper_diff.py` parses snapper's status output format. `changes.py` computes which files changed and filters them through git's ignore rules.
- **`dfu/package/`** — package config (`dfu_config.json`), patch config (`config.json` inside patches), ACL file handling.
- **`dfu/revision/`** — thin wrappers around git subprocess calls (`git init`, `git apply --3way`, `git bundle`, `git diff`, etc.).
- **`dfu/api/`** — `Store` (Redux-like immutable state container), `State` (frozen dataclass), `Playground` (temporary git repo manager), plugin interface.
- **`dfu/plugins/`** — event-driven plugins: autosave (auto-commits package changes), pacman (tracks installed/removed packages).
- **`dfu/helpers/`** — `@handle_errors` decorator for CLI commands, `JsonSerializableMixin`, subshell launcher.

Many operations call `sudo` for snapper/btrfs/proot. In tests, `subprocess.run` is mocked to strip `sudo`.

## Build & Test Commands

**All commands require `uv run`. Never use bare `pytest`, `ruff`, or `mypy`.**

```bash
uv sync                    # Install dependencies
uv run dfu                 # Run the CLI

uv run pytest tests                                    # All tests
uv run pytest tests/test_config.py                     # One file
uv run pytest tests/test_config.py::test_valid_config  # One test
uv run pytest -k "test_valid"                          # By pattern

uv run ruff check --fix . && uv run ruff format .     # Fix lint + format
uv run mypy --install-types --non-interactive dfu tests  # Type check
```

Makefile shortcuts: `make test`, `make fix`, `make typing`, `make all`.
Before submitting: `make all && make test`.

## Architecture Patterns

### Immutable State

State objects are frozen dataclasses. Updates use `dataclasses.replace()` via an `.update()` method with `TypedDict`/`Unpack` for type-safe kwargs.
Use `tuple` (not `list`) for immutable sequences and `MappingProxyType` for immutable dicts.

### Store (Redux-like)

`Store` holds a `State`. Changes go through `store.state = store.state.update(...)`. Subscribers are notified via `Callback = Callable[[State, State], None]`.

### Serialization

`msgspec` for JSON and TOML. `JsonSerializableMixin` provides `from_file()`, `from_json()`, `write()`.

### Error Handling

No custom exception classes. Use `ValueError` for validation, `FileNotFoundError` for missing files. `subprocess.run(check=True)` lets `CalledProcessError` propagate. The `@handle_errors` decorator on CLI commands catches these and exits with code 1.

## Code Conventions

- **mypy strict** — all functions need full type annotations including `-> None`
- Use `Path` for filesystem paths, never raw strings
- Frozen dataclasses for data objects; `@override` when overriding methods
- `__init__.py` files export explicit `__all__` lists

## Testing

- pytest with `conftest.py` fixtures; `tmp_path` for filesystem tests
- `click.testing.CliRunner` for CLI tests
- Git tests use a `setup_git` fixture that inits a repo with user config
- `subprocess.run` mocked in tests to strip `sudo` for CI
