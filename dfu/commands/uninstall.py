import subprocess
from pathlib import Path
from shutil import copy2, rmtree
from tempfile import mkdtemp
from textwrap import dedent

import click
from unidiff import PatchedFile, PatchSet

from dfu.api import Event, Store
from dfu.helpers.copy_files import copy_dry_run_files
from dfu.package.uninstall import Uninstall
from dfu.revision.git import git_add, git_apply, git_commit, git_init


def begin_uninstall(store: Store):
    if store.state.uninstall is not None:
        raise ValueError('Uninstallation is already in progress. Run dfu uninstall --continue to continue removal.')

    store.state = store.state.update(uninstall=Uninstall())
    continue_uninstall(store)


def continue_uninstall(store: Store):
    if store.state.uninstall is None:
        raise ValueError('There is no in-progress uninstallation. Run dfu uninstall to begin.')

    if not store.state.uninstall.dry_run_dir:
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
        store.state = store.state.update(uninstall=store.state.uninstall.update(dry_run_dir=str(dry_run_dir)))
        click.echo(
            dedent(
                f"""\
                Completed a dry run of the patches here: {dry_run_dir}
                Make any necessary changes to the files in that directory.
                Once you're satisfied, run dfu uninstall --continue to apply the patches to the system
                If everything looks good, run dfu uninstall --continue to continue removal""",
            ),
            err=True,
        )
        return

    if not store.state.uninstall.copied_files:
        copy_dry_run_files(Path(store.state.uninstall.dry_run_dir))
        store.state = store.state.update(uninstall=store.state.uninstall.update(copied_files=True))
        assert store.state.uninstall

    if not store.state.uninstall.removed_dependencies:
        store.dispatch(Event.UNINSTALL_DEPENDENCIES)
        store.state = store.state.update(uninstall=store.state.uninstall.update(removed_dependencies=True))

    click.echo("Cleaning up...", err=True)
    abort_uninstall(store)


def abort_uninstall(store: Store):
    pass


def _copy_base_files(store: Store, dest: Path):
    patch_files = reversed(sorted(store.state.package_dir.glob('*.patch'), key=lambda p: p.name))
    base_files: set[Path] = set()
    for patch in patch_files:
        files: list[PatchedFile] = PatchSet(patch.read_text(), metadata_only=True)
        for file in files:
            if not file.target_file:
                continue
            source_path = Path(file.target_file)

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
    patch_files = reversed(sorted(store.state.package_dir.glob('*.patch'), key=lambda p: p.name))
    for patch in patch_files:
        try:
            git_apply(dest, patch, reverse=True)
        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to apply patch {patch.name}", err=True)
            click.echo(f"Try running dfu rebase to modify the patches", err=True)
            click.echo(e.output, err=True)

        git_add(dest, ['.'])
        git_commit(dest, f"Patch {patch.name}")
