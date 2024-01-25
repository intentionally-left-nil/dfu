import subprocess
from pathlib import Path
from shutil import rmtree
from textwrap import dedent

import click

from dfu.api import Event, Playground, Store
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
        playground = Playground(prefix="dfu_dry_run_")
        try:
            git_init(playground.location)
            _copy_base_files(store, playground)
            git_add(playground.location, ['.'])
            git_commit(playground.location, "Initial files")
            _apply_patches(store, playground.location)
        except Exception:
            playground.cleanup()
            raise
        store.state = store.state.update(uninstall=store.state.uninstall.update(dry_run_dir=str(playground.location)))
        click.echo(
            dedent(
                f"""\
                Completed a dry run of the patches here: {playground.location}
                Make any necessary changes to the files in that directory.
                Once you're satisfied, run dfu uninstall --continue to apply the patches to the system
                If everything looks good, run dfu uninstall --continue to continue removal""",
            ),
            err=True,
        )
        return

    if not store.state.uninstall.copied_files:
        playground = Playground(location=Path(store.state.uninstall.dry_run_dir))
        playground.copy_files_to_filesystem()
        store.state = store.state.update(uninstall=store.state.uninstall.update(copied_files=True))
        assert store.state.uninstall

    if not store.state.uninstall.removed_dependencies:
        store.dispatch(Event.UNINSTALL_DEPENDENCIES)
        store.state = store.state.update(uninstall=store.state.uninstall.update(removed_dependencies=True))

    click.echo("Cleaning up...", err=True)
    abort_uninstall(store)


def abort_uninstall(store: Store):
    if store.state.uninstall is not None and store.state.uninstall.dry_run_dir:
        rmtree(store.state.uninstall.dry_run_dir, ignore_errors=True)
    store.state = store.state.update(uninstall=None)


def _copy_base_files(store: Store, playground: Playground):
    patch_files = sorted(store.state.package_dir.glob('*.patch'), key=lambda p: p.name)
    files_to_copy: set[Path] = set()
    for patch in patch_files:
        files_to_copy.update(playground.list_files_in_patch(patch))

    playground.copy_files_from_filesystem(files_to_copy)


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
