import os
import subprocess
from typing import Literal

import click

from dfu.api import Store
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.helpers.subshell import subshell
from dfu.snapshots.proot import proot


def launch_snapshot_shell(store: Store, snapshot_index: int):
    snapshot_index = normalize_snapshot_index(store.state.package_config, snapshot_index)
    snapshot = store.state.package_config.snapshots[snapshot_index]
    shell = os.environ.get('SHELL', '/bin/bash')
    args = proot([shell], config=store.state.config, snapshot=snapshot, cwd="/")
    subprocess.run(args)


def launch_shell(store: Store, location: Literal['install_files', 'uninstall_files'] | None):
    if not location:
        if store.state.uninstall and store.state.uninstall.dry_run_dir:
            location = 'uninstall_files'
        elif store.state.install and store.state.install.dry_run_dir:
            location = 'install_files'
        else:
            raise ValueError("No shell directory found")
        click.echo(f"Autodetecting --location {location}", err=True)

    cwd: str
    match location:
        case 'install_files':
            if not store.state.install or not store.state.install.dry_run_dir:
                raise ValueError("No install directory found")
            cwd = store.state.install.dry_run_dir
        case 'uninstall_files':
            if not store.state.uninstall or not store.state.uninstall.dry_run_dir:
                raise ValueError("No uninstall directory found")
            cwd = store.state.uninstall.dry_run_dir

    click.echo(f"Launching shell @ {cwd}", err=True)
    subshell(cwd)
