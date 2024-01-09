from dfu.config import Config
from dfu.package.package_config import SnapshotMappingDeprecated
from dfu.snapshots.snapper import Snapper


def proot(args: list[str], config: Config, snapshot_mapping_deprecated: SnapshotMappingDeprecated) -> list[str]:
    mount_order = [x for x in config.btrfs.snapper_configs if x in snapshot_mapping_deprecated]
    if len(mount_order) == 0:
        raise ValueError('No snapshots to mount')

    if len(mount_order) != len(snapshot_mapping_deprecated):
        raise ValueError('Not all snapshots are listed in the snapper_configs section of the config')

    root_config = Snapper(mount_order[0])
    proot_args = [
        'sudo',
        'proot',
        '-r',
        str(root_config.get_snapshot_path(snapshot_mapping_deprecated[mount_order[0]])),
    ]
    for snapper_config in mount_order[1:]:
        snapper = Snapper(snapper_config)
        source_dir = snapper.get_snapshot_path(snapshot_mapping_deprecated[snapper_config])
        dest_dir = snapper.get_mountpoint()
        proot_args.extend(['-b', f'{source_dir}:{dest_dir}'])

    proot_args.extend(['-b', '/dev', '-b', '/proc'])

    return proot_args + args
