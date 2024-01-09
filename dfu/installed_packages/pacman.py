import subprocess
from collections import namedtuple

from dfu.config import Config
from dfu.package.package_config import SnapshotMapping
from dfu.snapshots.proot import proot

Diff = namedtuple('Diff', ['added', 'removed'])


def get_installed_packages(config: Config, snapshot_mapping_deprecated: SnapshotMapping | None = None):
    args = ['pacman', '-Qqe']
    if snapshot_mapping_deprecated:
        args = proot(args, config=config, snapshot_mapping_deprecated=snapshot_mapping_deprecated)

    result = subprocess.run(args, capture_output=True, text=True, check=True)
    packages = result.stdout.split('\n')
    packages = [package.strip() for package in packages]
    packages = [package for package in packages if package]
    packages.sort()
    return packages


def diff_packages(old_packages: list[str], new_packages: list[str]) -> Diff:
    old = set(old_packages)
    new = set(new_packages)
    return Diff(added=new - old, removed=old - new)
