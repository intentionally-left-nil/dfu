from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig, Snapshot
from dfu.snapshots.snapper import Snapper


def create_pre_snapshot(config: Config, package_dir: Path):
    package_config = PackageConfig.from_file(package_dir / "dfu_config.json")
    snapshots_deprecated: dict[str, Snapshot] = {}
    for snapper_config in config.btrfs.snapper_configs:
        snapper = Snapper(snapper_config)
        pre_id = snapper.create_pre_snapshot(package_config.description or package_config.name)
        snapshots_deprecated[snapper_config] = Snapshot(pre_id=pre_id)
    package_config.snapshots_deprecated.append(snapshots_deprecated)
    package_config.write(package_dir / "dfu_config.json")


def create_post_snapshot(package_dir: Path):
    package_config = PackageConfig.from_file(package_dir / "dfu_config.json")
    if len(package_config.snapshots_deprecated) == 0:
        raise ValueError("No existing pre-snapshots_deprecated found")

    snapshots_deprecated = package_config.snapshots_deprecated[-1]
    if any(snapshot.post_id is not None for snapshot in snapshots_deprecated.values()):
        raise ValueError("Post-snapshot already exists")

    for snapper_config, snapshot in snapshots_deprecated.items():
        snapper = Snapper(snapper_config)
        post_id = snapper.create_post_snapshot(snapshot.pre_id, package_config.description or package_config.name)
        snapshot.post_id = post_id
    package_config.write(package_dir / "dfu_config.json")
