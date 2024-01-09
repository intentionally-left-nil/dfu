from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig
from dfu.snapshots.snapper import Snapper


def create_snapshot(config: Config, package_dir: Path):
    package_config = PackageConfig.from_file(package_dir / "dfu_config.json")
    snapshot: dict[str, int] = {}
    for snapper_config in config.btrfs.snapper_configs:
        snapper = Snapper(snapper_config)
        snapshot_id = snapper.create_snapshot(package_config.description or package_config.name)
        snapshot[snapper_config] = snapshot_id
    package_config.snapshots.append(snapshot)
    package_config.write(package_dir / "dfu_config.json")
