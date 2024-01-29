import subprocess
from types import MappingProxyType

from dfu.api import Store
from dfu.revision.git import git_check_ignore
from dfu.snapshots.proot import proot
from dfu.snapshots.snapper import Snapper
from dfu.snapshots.snapper_diff import FileChangeAction, SnapperDiff


def files_modified(store: Store, *, from_index: int, to_index: int, only_ignored: bool) -> dict[str, set[str]]:
    """Returns a dict of snapper_name -> set of files modified between the two snapshots."""
    pre_snapshot = store.state.package_config.snapshots[from_index]
    post_snapshot = store.state.package_config.snapshots[to_index]
    files_modified: dict[str, set[str]] = dict()
    for snapper_name, pre_id in pre_snapshot.items():
        post_id = post_snapshot[snapper_name]
        snapper = Snapper(snapper_name)
        deltas = snapper.get_delta(pre_id, post_id)

        ignored_files: set[str] = set(
            git_check_ignore(store.state.package_dir, [f"files/{delta.path.removeprefix('/')}" for delta in deltas])
        )
        ignored_files = {p.removeprefix("files") for p in ignored_files}
        if only_ignored:
            deltas = [d for d in deltas if d.path in ignored_files]
        else:
            deltas = [d for d in deltas if d.path not in ignored_files]

        changes: set[str] = set()
        for delta in deltas:
            snapshot = pre_snapshot if delta.action == FileChangeAction.deleted else post_snapshot
            if is_file(store, snapshot, delta.path):
                changes.add(delta.path)

        files_modified[snapper_name] = changes
    return files_modified


def is_file(store: Store, snapshot: MappingProxyType[str, int], path: str) -> bool:
    args = proot(
        ["/bin/sh", "-c", 'test -f "$1" || test -L "$1"', "_", path],
        config=store.state.config,
        snapshot=snapshot,
        cwd="/",
    )
    return subprocess.run(args, capture_output=True).returncode == 0
