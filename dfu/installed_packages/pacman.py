import subprocess
from collections import namedtuple

Diff = namedtuple('Diff', ['added', 'removed'])


def get_installed_packages():
    result = subprocess.run(['pacman', '-Qqe'], capture_output=True, text=True, check=True)
    packages = result.stdout.split('\n')
    packages = [package.strip() for package in packages]
    packages = [package for package in packages if package]
    packages.sort()
    return packages


def diff_packages(old_packages: list[str], new_packages: list[str]) -> Diff:
    old = set(old_packages)
    new = set(new_packages)
    return Diff(added=new - old, removed=old - new)
