from dfu.api import Store
from dfu.revision.git import git_check_ignore
from dfu.snapshots.snapper import Snapper


def files_modified(store: Store, *, from_index: int, to_index: int, only_ignored: bool) -> set[str]:
    pre_snapshot = store.state.package_config.snapshots[from_index]
    post_snapshot = store.state.package_config.snapshots[to_index]
    files = set()
    for snapper_name, pre_id in pre_snapshot.items():
        post_id = post_snapshot[snapper_name]
        snapper = Snapper(snapper_name)
        deltas = snapper.get_delta(pre_id, post_id)
        files |= {f"files/{delta.path.removeprefix('/')}" for delta in deltas}

    ignored_files = set(git_check_ignore(store.state.package_dir, files))
    modified_files = ignored_files if only_ignored else files - ignored_files
    return {file.removeprefix('files') for file in modified_files}
