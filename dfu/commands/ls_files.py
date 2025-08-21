import click

from dfu.api import Store
from dfu.helpers.normalize_snapshot_index import normalize_snapshot_index
from dfu.snapshots.changes import files_modified


def ls_files(store: Store, *, from_index: int, to_index: int, only_ignored: bool) -> None:
    from_index = normalize_snapshot_index(store.state.package_config, from_index)
    to_index = normalize_snapshot_index(store.state.package_config, to_index)
    if from_index > to_index:
        raise ValueError(f"from_index {from_index} is greater than to_index {to_index}")
    for files in files_modified(store, from_index=from_index, to_index=to_index, only_ignored=only_ignored).values():
        merged = files.pre_files | files.post_files
        for file in merged:
            click.echo(file)
