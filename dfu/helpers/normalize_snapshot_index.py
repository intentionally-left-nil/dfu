from dfu.package.package_config import PackageConfig


def normalize_snapshot_index(package_config: PackageConfig, index: int) -> int:
    if index < 0:
        index += len(package_config.snapshots)
    if index < 0 or index >= len(package_config.snapshots):
        raise ValueError(f"index {index} is out of bounds")
    return index
