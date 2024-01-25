from pathlib import Path
from shutil import rmtree
from textwrap import dedent

import click

from dfu.api import Event, Playground, Store
from dfu.package.uninstall import Uninstall
from dfu.revision.git import git_add, git_are_files_staged, git_commit, git_init


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
            if git_are_files_staged(playground.location):
                git_commit(playground.location, "Initial files")
        except Exception:
            playground.cleanup()
            raise
        patch_files = list(reversed(sorted(store.state.package_dir.glob('*.patch'), key=lambda p: p.name)))
        store.state = store.state.update(
            uninstall=store.state.uninstall.update(
                dry_run_dir=str(playground.location), patches_to_apply=[str(p) for p in patch_files]
            )
        )
        assert store.state.uninstall and store.state.uninstall.dry_run_dir
    playground = Playground(location=Path(store.state.uninstall.dry_run_dir))
    if store.state.uninstall.patches_to_apply:
        (succeeded, remaining) = playground.apply_patches([Path(p) for p in store.state.uninstall.patches_to_apply])
        store.state = store.state.update(
            uninstall=store.state.uninstall.update(patches_to_apply=[str(p) for p in remaining])
        )
        if remaining or not succeeded:
            click.echo(
                dedent(
                    """\
                    There was a merge conflict applying the patches. Run dfu shell, and resolve the conflicts.
                    Once completed, commit the changes, and then run dfu uninstall --continue"""
                )
            )
        else:
            click.echo(
                dedent(
                    """\
                    A dry run of the file changes are ready for your approval.
                    Run dfu shell to view the changes, and make any necessary modifications.
                    Once satisfied, run dfu uninstall --continue"""
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
