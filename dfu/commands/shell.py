import os
import subprocess
from typing import Literal

import click

from dfu.api import Store
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.snapshots.proot import proot


def launch_snapshot_shell(store: Store, snapshot_index: int):
    snapshot_index = normalize_snapshot_index(store.state.package_config, snapshot_index)
    snapshot = store.state.package_config.snapshots[snapshot_index]
    args = proot([_get_shell()], config=store.state.config, snapshot=snapshot, cwd="/")
    subprocess.run(args)


def launch_shell(
    store: Store, location: Literal['placeholder', 'diff_files', 'install_files', 'uninstall_files'] | None
):
    if not location:
        if store.state.uninstall and store.state.uninstall.dry_run_dir:
            location = 'uninstall_files'
        elif store.state.install and store.state.install.dry_run_dir:
            location = 'install_files'
        elif store.state.diff and store.state.diff.working_dir:
            location = 'diff_files'
        elif store.state.diff and store.state.diff.placeholder_dir:
            location = 'placeholder'
        else:
            raise ValueError("No shell directory found")
        click.echo(f"Autodetecting --location {location}", err=True)

    cwd: str
    match location:
        case 'placeholder':
            if not store.state.diff or not store.state.diff.placeholder_dir:
                raise ValueError("No placeholder directory found")
            cwd = store.state.diff.placeholder_dir
        case 'diff_files':
            if not store.state.diff or not store.state.diff.working_dir:
                raise ValueError("No diff directory found")
            cwd = store.state.diff.working_dir
        case 'install_files':
            if not store.state.install or not store.state.install.dry_run_dir:
                raise ValueError("No install directory found")
            cwd = store.state.install.dry_run_dir
        case 'uninstall_files':
            if not store.state.uninstall or not store.state.uninstall.dry_run_dir:
                raise ValueError("No uninstall directory found")
            cwd = store.state.uninstall.dry_run_dir

    click.echo(f"Launching shell @ {cwd}", err=True)
    subprocess.run([_get_shell()], cwd=cwd)


def _get_shell():
    return os.environ.get('SHELL', '/bin/bash')
