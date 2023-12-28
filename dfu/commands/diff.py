from pathlib import Path

from dfu.config import Config
from dfu.installed_packages.pacman import diff_packages, get_installed_packages
from dfu.package.package_config import PackageConfig
from dfu.snapshots.snapper import Snapper


def diff_snapshot(config: Config, package_config_path: Path):
    package_config = PackageConfig.from_file(package_config_path)
    update_installed_packages(config, package_config)
    create_changed_placeholders(config, package_config)
    package_config.write(package_config_path)


def update_installed_packages(config: Config, package_config: PackageConfig):
    if len(package_config.snapshots) == 0:
        raise ValueError('Did not create a successful pre/post snapshot pair')
    old_packages = get_installed_packages(config, package_config.snapshot_mapping(use_pre_id=True))
    new_packages = get_installed_packages(config, package_config.snapshot_mapping(use_pre_id=False))

    diff = diff_packages(old_packages, new_packages)
    package_config.programs_added = diff.added
    package_config.programs_removed = diff.removed


def create_changed_placeholders(config: Config, package_config: PackageConfig):
    pre_mapping = package_config.snapshot_mapping(use_pre_id=True)
    post_mapping = package_config.snapshot_mapping(use_pre_id=False)

    placeholder_dir = config.get_package_dir() / package_config.name / 'placeholders'
    placeholder_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    for snapper_name, pre_id in pre_mapping.items():
        post_id = post_mapping[snapper_name]
        snapper = Snapper(snapper_name)
        for change in snapper.get_delta(pre_id, post_id):
            path = placeholder_dir / change.path.lstrip('/')
            path.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            path.write_text(f"PLACEHOLDER: {change.action}")
