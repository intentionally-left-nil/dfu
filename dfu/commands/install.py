import subprocess
from pathlib import Path
from shutil import rmtree
from textwrap import dedent

import click

from dfu.api import Event, Playground, Store
from dfu.package.install import Install
from dfu.revision.git import git_add, git_are_files_staged, git_commit, git_init


def begin_install(store: Store):
    if store.state.install is not None:
        raise ValueError('Installation is already in progress. Run dfu install --continue to continue installation.')

    store.state = store.state.update(install=Install())
    continue_install(store)


def continue_install(store: Store):
    if store.state.install is None:
        raise ValueError('There is no in-progress installation. Run dfu install to begin installation.')

    if not store.state.install.installed_dependencies:
        store.dispatch(Event.INSTALL_DEPENDENCIES)
        store.state = store.state.update(install=store.state.install.update(installed_dependencies=True))
        assert store.state.install

    if not store.state.install.dry_run_dir:
        playground = Playground(prefix="dfu_dry_run_")
        try:
            git_init(playground.location)
            _copy_base_files(store, playground)
            git_add(playground.location, ['.'])
            if git_are_files_staged(playground.location):
                git_commit(playground.location, "Initial files")
            patch_files = sorted(store.state.package_dir.glob('*.patch'), key=lambda p: p.name)
            if not playground.apply_patches(patch_files):
                click.echo("There were merge conflicts applying the patches. Run dfu shell to address them", err=True)

        except Exception:
            playground.cleanup()
            raise

        store.state = store.state.update(install=store.state.install.update(dry_run_dir=str(playground.location)))
        click.echo(
            dedent(
                """\
                A dry run of the file changes are ready for your approval.
                Run dfu shell to view the changes, and make any necessary modifications.
                Once satisfied, run dfu install --continue"""
            ),
            err=True,
        )
        return

    if not store.state.install.copied_files:
        playground = Playground(location=Path(store.state.install.dry_run_dir))
        playground.copy_files_to_filesystem()
        store.state = store.state.update(install=store.state.install.update(copied_files=True))
    click.echo("Cleaning up...", err=True)
    abort_install(store)


def abort_install(store: Store):
    if store.state.install is not None and store.state.install.dry_run_dir:
        rmtree(store.state.install.dry_run_dir, ignore_errors=True)
    store.state = store.state.update(install=None)


def _copy_base_files(store: Store, playground: Playground):
    patch_files = sorted(store.state.package_dir.glob('*.patch'), key=lambda p: p.name)
    files_to_copy: set[Path] = set()
    for patch in patch_files:
        files_to_copy.update(playground.list_files_in_patch(patch))

    playground.copy_files_from_filesystem(files_to_copy)
