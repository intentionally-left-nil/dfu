from pathlib import Path

from dfu.config import Config
from dfu.installed_packages.pacman import diff_packages, get_installed_packages
from dfu.package.package_config import PackageConfig


def diff_snapshot(config: Config, package_config_path: Path):
    package_config = PackageConfig.from_file(package_config_path)
    update_installed_packages(config, package_config)
    package_config.write(package_config_path)


def update_installed_packages(config: Config, package_config: PackageConfig):
    if len(package_config.snapshots) == 0:
        raise ValueError('Did not create a successful pre/post snapshot pair')
    old_packages = get_installed_packages(config, package_config.snapshot_mapping(use_pre_id=True))
    new_packages = get_installed_packages(config, package_config.snapshot_mapping(use_pre_id=False))

    diff = diff_packages(old_packages, new_packages)
    package_config.programs_added = diff.added
    package_config.programs_removed = diff.removed
