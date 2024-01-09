from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig, SnapshotDeprecated
from dfu.snapshots.snapper import Snapper


def create_pre_snapshot(config: Config, package_dir: Path):
    package_config = PackageConfig.from_file(package_dir / "dfu_config.json")
    snapshots_deprecated: dict[str, SnapshotDeprecated] = {}
    for snapper_config in config.btrfs.snapper_configs:
        snapper = Snapper(snapper_config)
        pre_id = snapper.create_pre_snapshot(package_config.description or package_config.name)
        snapshots_deprecated[snapper_config] = SnapshotDeprecated(pre_id=pre_id)
    package_config.snapshots_deprecated.append(snapshots_deprecated)
    package_config.write(package_dir / "dfu_config.json")
