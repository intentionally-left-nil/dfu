import subprocess
from pathlib import Path
from shutil import copy2, rmtree
from tempfile import mkdtemp
from textwrap import dedent

import click
from unidiff import PatchedFile, PatchSet
from unidiff.constants import DEV_NULL

from dfu.api import Event, Store
from dfu.package.install import Install
from dfu.revision.git import git_add, git_apply, git_commit, git_init


def begin_install(store: Store):
    if store.state.install is not None:
        raise ValueError('Installation is already in progress. Run dfu install --continue to continue installation.')

    store.state = store.state.update(install=Install())
    continue_install(store)


def continue_install(store: Store):
    if store.state.install is None:
        raise ValueError('There is no in-progress installation. Run dfu install --begin to begin installation.')

    if not store.state.install.installed_dependencies:
        store.dispatch(Event.INSTALL_DEPENDENCIES)
        store.state = store.state.update(install=store.state.install.update(installed_dependencies=True))
        assert store.state.install

    if not store.state.install.dry_run_dir:
        dry_run_dir = Path(mkdtemp(prefix="dfu_dry_run_"))
        try:
            git_init(dry_run_dir)
            _copy_base_files(store, dry_run_dir)
            git_add(dry_run_dir, ['.'])
            git_commit(dry_run_dir, "Initial files")
            _apply_patches(store, dry_run_dir)
        except Exception:
            rmtree(dry_run_dir, ignore_errors=True)
            raise

        store.state = store.state.update(install=store.state.install.update(dry_run_dir=str(dry_run_dir)))
        click.echo(
            dedent(
                f"""\
                Completed a dry run of the patches here: {dry_run_dir}
                Make any necessary changes to the files in that directory.
                Once you're satisfied, run dfu install --continue to apply the patches to the system
                If everything looks good, run dfu install --continue to continue installation""",
            ),
            err=True,
        )
    click.echo("Cleaning up...", err=True)
    abort_install(store)


def abort_install(store: Store):
    if store.state.install is not None and store.state.install.dry_run_dir:
        rmtree(store.state.install.dry_run_dir, ignore_errors=True)
    store.state = store.state.update(install=None)


def _copy_base_files(store: Store, dest: Path):
    patch_files = sorted(store.state.package_dir.glob('*.patch'), key=lambda p: p.name)
    base_files: set[Path] = set()
    for patch in patch_files:
        files: list[PatchedFile] = PatchSet(patch.read_text(), metadata_only=True)
        for file in files:
            source_path = Path(file.source_file)
            if source_path == Path(DEV_NULL) or source_path.parts[1:] == Path(DEV_NULL).parts[1:]:
                continue

            if len(source_path.parts) < 3 or source_path.parts[1] != "files":
                raise ValueError(f"Unexpected source file path: {source_path}")

            base_files.add(Path(*source_path.parts[2:]))

    for base_file in base_files:
        target = dest / 'files' / base_file
        target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        try:
            copy2(Path('/') / base_file, target)
        except PermissionError:
            subprocess.run(
                ["sudo", "cp", "-p", (Path('/') / base_file).resolve(), dest.resolve()], check=True, capture_output=True
            )


def _apply_patches(store: Store, dest: Path):
    patch_files = sorted(store.state.package_dir.glob('*.patch'), key=lambda p: p.name)
    for patch in patch_files:
        try:
            git_apply(dest, patch)
        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to apply patch {patch.name}", err=True)
            click.echo(f"Try running dfu rebase to modify the patches", err=True)
            click.echo(e.output, err=True)

        git_add(dest, ['.'])
        git_commit(dest, f"Patch {patch.name}")
