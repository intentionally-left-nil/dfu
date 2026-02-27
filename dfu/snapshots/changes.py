import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

from dfu.api import Store
from dfu.package.acl_file import AclEntry, AclFile
from dfu.revision.git import git_check_ignore
from dfu.snapshots.proot import proot
from dfu.snapshots.snapper import Snapper, SnapperName
from dfu.snapshots.snapper_diff import FileChangeAction


@dataclass
class FilesModified:
    pre_files: set[str]
    post_files: set[str]


def files_modified(
    store: Store, *, from_index: int, to_index: int, only_ignored: bool
) -> dict[SnapperName, FilesModified]:
    """Returns a dict of snapper_name -> set of files modified between the two snapshots."""
    pre_snapshot = store.state.package_config.snapshots[from_index]
    post_snapshot = store.state.package_config.snapshots[to_index]
    files_modified: dict[SnapperName, FilesModified] = {}
    for snapper_name, pre_id in pre_snapshot.items():
        post_id = post_snapshot[snapper_name]
        snapper = Snapper(snapper_name)
        deltas = snapper.get_delta(pre_id, post_id)

        ignored_files: set[str] = set(
            git_check_ignore(
                store.state.package_dir,
                [f"files/{delta.path.removeprefix('/')}" for delta in deltas],
            )
        )
        ignored_files = {p.removeprefix("files") for p in ignored_files}
        if only_ignored:
            deltas = [d for d in deltas if d.path in ignored_files]
        else:
            deltas = [d for d in deltas if d.path not in ignored_files]

        pre_files_to_check = set(
            [
                delta.path
                for delta in deltas
                if delta.action not in (FileChangeAction.created, FileChangeAction.no_change)
            ]
        )
        pre_files = filter_files(store, pre_snapshot, pre_files_to_check)

        post_files_to_check = set(
            [
                delta.path
                for delta in deltas
                if delta.action not in (FileChangeAction.deleted, FileChangeAction.no_change)
            ]
        )
        post_files = filter_files(store, post_snapshot, post_files_to_check)
        files_modified[snapper_name] = FilesModified(pre_files=pre_files, post_files=post_files)
    return files_modified


def filter_files(store: Store, snapshot: MappingProxyType[SnapperName, int], paths: set[str]) -> set[str]:
    if len(paths) == 0:
        # Performance optimization: Suprocess.run() takes several hundred milliseconds.
        # Since this is called before & after for each snapper config, there are many potentially empty calls
        return set()
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
    return set(p for p in result.stdout.splitlines())


def get_permissions(store: Store, *, files_modified: dict[SnapperName, set[str]], snapshot_index: int) -> AclFile:
    """Returns an AclFile containing permission metadata for the files and folders in a given snapshot
    Each entry contains a path, mode, uid, and gid.
    For example, given a Snapper snapshot mounted at /home with a file /home/user/file.txt
    this might return an AclFile with entries like:
    [
        AclEntry(Path("/home/user/"), "755", "user", "user"),
        AclEntry(Path("/home/user/file.txt"), "644", "user", "user"),
    ]
    """
    entries: dict[Path, AclEntry] = {}
    snapshot = store.state.package_config.snapshots[snapshot_index]
    for snapper_name, paths in files_modified.items():
        paths = filter_files(store, snapshot, paths)
        snapper = Snapper(snapper_name)
        mountpoint = snapper.get_mountpoint()
        snapshot_dir = snapper.get_snapshot_path(snapshot[snapper_name])
        sub_path_directories: set[Path] = set()
        for path in paths:
            sub_path = Path(path).relative_to(mountpoint)
            src = snapshot_dir / sub_path
            dest = Path(os.path.abspath(str(mountpoint / sub_path)))
            stats = subprocess.run(
                ["sudo", "stat", "-c", "%F#%a#%U#%G", str(src)],
                capture_output=True,
                text=True,
                check=True,
            )
            file_type, mode, uid, gid = stats.stdout.strip().split("#")

            if file_type in [
                "directory",
                "regular file",
                "regular empty file",
                "symlink",
                "symbolic link",
            ]:
                if file_type == "directory":
                    sub_path_directories.add(sub_path)
                else:
                    for parent in sub_path.parents:
                        sub_path_directories.add(parent)
                entries[dest] = AclEntry(dest, mode, uid, gid)
            else:
                print(f"{dest} is an unhandled file type. Ignoring", file=sys.stderr)
                continue
        sub_path_directories.discard(Path("."))
        for sub_path in sub_path_directories:
            dest = mountpoint / sub_path
            dir_src = os.path.abspath(snapshot_dir / sub_path)
            stats = subprocess.run(
                ["sudo", "stat", "-c", "%a#%U#%G", dir_src],
                capture_output=True,
                text=True,
                check=True,
            )
            mode, uid, gid = stats.stdout.strip().split("#")
            entries[dest] = AclEntry(dest, mode, uid, gid)

    return AclFile(entries)
