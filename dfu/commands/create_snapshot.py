from pathlib import Path

from dfu.api.store import Store
from dfu.config import Config
from dfu.package.package_config import PackageConfig
from dfu.snapshots.snapper import Snapper


def create_snapshot(store: Store):
    assert store.state.config and store.state.package_config and store.state.package_dir
    snapshot: dict[str, int] = {}
    for snapper_config in store.state.config.btrfs.snapper_configs:
        snapper = Snapper(snapper_config)
        snapshot_id = snapper.create_snapshot(store.state.package_config.description or store.state.package_config.name)
        snapshot[snapper_config] = snapshot_id
    store.state.package_config.snapshots.append(snapshot)
    store.state.package_config.write(store.state.package_dir / "dfu_config.json")
