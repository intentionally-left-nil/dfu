import subprocess
from collections import namedtuple

from dfu.config import Config
from dfu.snapshots.proot import proot

Diff = namedtuple('Diff', ['added', 'removed'])


def get_installed_packages(config: Config, snapshot: dict[str, int] | None = None):
    args = ['pacman', '-Qqe']
    if snapshot:
        args = proot(args, config=config, snapshot=snapshot)

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
