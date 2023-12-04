from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig, Snapshot
from dfu.snapshots.snapper import Snapper


def create_pre_snapshot(config: Config, package_config_path: Path):
    package_config = PackageConfig.from_file(package_config_path)
    snapshots: dict[str, Snapshot] = {}
    for snapper_config in config.btrfs.snapper_configs:
        snapper = Snapper(snapper_config)
        pre_id = snapper.create_pre_snapshot(package_config.description or package_config.name)
        snapshots[snapper_config] = Snapshot(pre_id=pre_id)
    package_config.snapshots.append(snapshots)
    package_config.write(package_config_path)


def create_post_snapshot(package_config_path: Path):
    package_config = PackageConfig.from_file(package_config_path)
    if len(package_config.snapshots) == 0:
        raise ValueError("No existing pre-snapshots found")

    snapshots = package_config.snapshots[-1]
    if any(snapshot.post_id is not None for snapshot in snapshots.values()):
        raise ValueError("Post-snapshot already exists")

    for snapper_config, snapshot in snapshots.items():
        snapper = Snapper(snapper_config)
        post_id = snapper.create_post_snapshot(snapshot.pre_id, package_config.description or package_config.name)
        snapshot.post_id = post_id
    package_config.write(package_config_path)
