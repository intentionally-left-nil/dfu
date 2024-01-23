import os
import subprocess

from dfu.api import Store
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.snapshots.proot import proot


def chroot_shell(store: Store, snapshot_index: int):
    snapshot_index = normalize_snapshot_index(store.state.package_config, snapshot_index)
    snapshot = store.state.package_config.snapshots[snapshot_index]
    shell = os.environ.get('SHELL', '/bin/bash')
    args = proot([shell], config=store.state.config, snapshot=snapshot)
    subprocess.call(args, shell=True)
