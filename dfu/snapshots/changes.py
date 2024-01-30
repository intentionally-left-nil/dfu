import subprocess
from types import MappingProxyType

from dfu.api import Store
from dfu.revision.git import git_check_ignore
from dfu.snapshots.proot import proot
from dfu.snapshots.snapper import Snapper
from dfu.snapshots.snapper_diff import FileChangeAction, SnapperDiff


def files_modified(store: Store, *, from_index: int, to_index: int, only_ignored: bool) -> dict[str, list[str]]:
    """Returns a dict of snapper_name -> set of files modified between the two snapshots."""
    pre_snapshot = store.state.package_config.snapshots[from_index]
    post_snapshot = store.state.package_config.snapshots[to_index]
    files_modified: dict[str, list[str]] = dict()
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

        pre_files_to_check = [delta.path for delta in deltas if delta.action == FileChangeAction.deleted]
        pre_files = filter_files(store, pre_snapshot, pre_files_to_check)

        post_files_to_check = [delta.path for delta in deltas if delta.action != FileChangeAction.deleted]
        post_files = filter_files(store, post_snapshot, post_files_to_check)
        files_modified[snapper_name] = pre_files + post_files
    return files_modified


def filter_files(store: Store, snapshot: MappingProxyType[str, int], paths: list[str]) -> list[str]:
    if len(paths) == 0:
        # Performance optimization: Suprocess.run() takes several hundred milliseconds.
        # Since this is called before & after for each snapper config, there are many potentially empty calls
        return []
    script = """\
while IFS= read -r -d $'\\0' path ; do
    if [ -f "$path" ] || [ -L "$path" ] ; then
        echo "$path"
    fi
done
"""
    args = proot(
        ["/bin/bash", "-c", script],
        config=store.state.config,
        snapshot=snapshot,
        cwd="/",
    )
    # Important: use the null character as the delimiter (and read -d '') since that can't appear in a filename
    # Also important: Send a trailing newline so that the last file is read
    result = subprocess.run(args, capture_output=True, text=True, input="\0".join(paths) + "\0")
    return [p for p in result.stdout.splitlines()]
