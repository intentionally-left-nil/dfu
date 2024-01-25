import os
import subprocess

from dfu.api import Store
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.snapshots.proot import proot


def launch_snapshot_shell(store: Store, snapshot_index: int):
    snapshot_index = normalize_snapshot_index(store.state.package_config, snapshot_index)
    snapshot = store.state.package_config.snapshots[snapshot_index]
    args = proot([_get_shell()], config=store.state.config, snapshot=snapshot, cwd="/")
    subprocess.run(args)


def launch_placeholder_shell(store: Store):
    if store.state.diff is None or store.state.diff.placeholder_dir is None:
        raise ValueError("No placeholder directory found")
    subprocess.run([_get_shell()], cwd=store.state.diff.placeholder_dir)


def launch_files_shell(store: Store):
    if store.state.diff is None or store.state.diff.working_dir is None:
        raise ValueError("No files directory found")
    subprocess.run([_get_shell()], cwd=store.state.diff.working_dir)


def _get_shell():
    return os.environ.get('SHELL', '/bin/bash')
