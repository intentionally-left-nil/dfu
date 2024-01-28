import click

from dfu.api import Store
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.revision.git import git_check_ignore
from dfu.snapshots.snapper import Snapper


def ls_files(store: Store, *, from_index: int, to_index: int, only_ignored: bool):
    for file in get_files(store, from_index=from_index, to_index=to_index, only_ignored=only_ignored):
        click.echo(file)


def get_files(store: Store, *, from_index: int, to_index: int, only_ignored: bool) -> set[str]:
    from_index = normalize_snapshot_index(store.state.package_config, from_index)
    to_index = normalize_snapshot_index(store.state.package_config, to_index)
    if from_index > to_index:
        raise ValueError(f"from_index {from_index} is greater than to_index {to_index}")
    pre_snapshot = store.state.package_config.snapshots[from_index]
    post_snapshot = store.state.package_config.snapshots[to_index]

    files = set()
    for snapper_name, pre_id in pre_snapshot.items():
        post_id = post_snapshot[snapper_name]
        snapper = Snapper(snapper_name)
        deltas = snapper.get_delta(pre_id, post_id)
        files |= {f"files/{delta.path.lstrip('/')}" for delta in deltas}

    ignored_files = set(git_check_ignore(store.state.package_dir, files))
    return ignored_files if only_ignored else files - ignored_files
