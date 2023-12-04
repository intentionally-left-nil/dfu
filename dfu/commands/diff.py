import os
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

from dfu.installed_packages.pacman import diff_packages, get_installed_packages
from dfu.package.package_config import PackageConfig, Snapshot
from dfu.snapshots.snapper import Snapper


def diff_snapshot(package_config_path: Path):
    package_config = PackageConfig.from_file(package_config_path)
    update_installed_packages(package_config)
    package_config.write(package_config_path)


def update_installed_packages(package_config: PackageConfig):
    if len(package_config.snapshots) == 0:
        raise ValueError('Did not create a successful pre/post snapshot pair')
    snapshots = package_config.snapshots[-1]

    with mount_snapshots(snapshots, mount_pre_snapshot=True) as mountpoint:
        with chroot(mountpoint):
            old_packages = get_installed_packages()

    with mount_snapshots(snapshots, mount_pre_snapshot=False) as mountpoint:
        with chroot(mountpoint):
            new_packages = get_installed_packages()

    diff = diff_packages(old_packages, new_packages)
    package_config.programs_added = diff.added
    package_config.programs_removed = diff.removed


@contextmanager
def mount_snapshots(snapshots: dict[str, Snapshot], *, mount_pre_snapshot: bool) -> Generator[str, None, None]:
    with TemporaryDirectory() as tempdir:
        for snapper_config, snapshot in snapshots.items():
            snapper = Snapper(snapper_config)
            snapshot_id = snapshot.pre_id if mount_pre_snapshot else snapshot.post_id
            if snapshot_id is None:
                raise ValueError('Cannot mount a snapshot that does not exist')
            snapper.mount_snapshot(snapshot_id, tempdir)
        yield tempdir


@contextmanager
def chroot(mountpoint: str) -> Generator[None, None, None]:
    old_root = os.open("/", os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.chroot(mountpoint)
        os.chdir("/")
        yield
    finally:
        os.fchdir(old_root)
        os.chroot('.')
        os.close(old_root)
