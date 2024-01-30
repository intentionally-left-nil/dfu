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
