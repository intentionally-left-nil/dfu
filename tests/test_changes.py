import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from dfu.api import Store
from dfu.package.acl_file import AclEntry
from dfu.revision.git import DEFAULT_GITIGNORE
from dfu.snapshots.changes import FilesModified, files_modified, filter_files, get_permissions
from dfu.snapshots.snapper import Snapper, SnapperName
from dfu.snapshots.snapper_diff import FileChangeAction, SnapperDiff


@pytest.fixture
def store(tmp_path: Path, request: pytest.FixtureRequest, setup_git: None) -> Store:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(DEFAULT_GITIGNORE)

    base_store: Store = request.getfixturevalue("store")
    base_store.state = base_store.state.update(
        package_dir=tmp_path,
        package_config=base_store.state.package_config.update(
            snapshots=(
                MappingProxyType({SnapperName("root"): 1}),
                MappingProxyType({SnapperName("root"): 2}),
            )
        ),
    )
    return base_store


@pytest.fixture
def store_with_user_snapper(tmp_path: Path, request: pytest.FixtureRequest, setup_git: None) -> Store:
    gitignore = tmp_path / ".gitignore"
    gitignore.write_text(DEFAULT_GITIGNORE)

    base_store: Store = request.getfixturevalue("store")
    base_store.state = base_store.state.update(
        package_dir=tmp_path,
        package_config=base_store.state.package_config.update(
            snapshots=(
                MappingProxyType({SnapperName("root"): 1, SnapperName("user"): 1}),
                MappingProxyType({SnapperName("root"): 2, SnapperName("user"): 2}),
            )
        ),
    )
    return base_store


@dataclass
class DeltaEntry:
    path: str
    action: FileChangeAction = FileChangeAction.created


@contextmanager
def mock_get_delta(responses: dict[str, list[DeltaEntry]]) -> Generator[MagicMock, None, None]:
    def side_effect(self: Any, pre_snapshot_id: int, post_snapshot_id: int) -> list[SnapperDiff]:
        response = responses[self.snapper_name]
        return [SnapperDiff(path=entry.path, action=entry.action, permissions_changed=False) for entry in response]

    with patch.object(Snapper, "get_delta", autospec=True) as mock_get_delta:
        mock_get_delta.side_effect = side_effect
        yield mock_get_delta


@pytest.fixture
def mock_filter_files() -> Generator[MagicMock, None, None]:
    def side_effect(store: Store, snapshot: MappingProxyType[SnapperName, int], paths: list[str]) -> list[str]:
        return paths

    with patch("dfu.snapshots.changes.filter_files", side_effect=side_effect) as mock_filter_files:
        yield mock_filter_files


def test_files_modified_no_snapshots(store: Store, mock_filter_files: MagicMock) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(snapshots=(MappingProxyType({}),))
    )
    with mock_get_delta({"root": []}):
        assert files_modified(store, from_index=0, to_index=0, only_ignored=False) == {}


def test_files_modified_no_changes(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": []}):
        result = files_modified(store, from_index=0, to_index=0, only_ignored=False)
        assert result == {"root": FilesModified(pre_files=set(), post_files=set())}


def test_files_modified_nothing_ignored(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": [DeltaEntry("/etc/test.conf"), DeltaEntry("/etc/test2.conf")]}):
        result = files_modified(store, from_index=0, to_index=1, only_ignored=False)
        assert result == {"root": FilesModified(pre_files=set(), post_files={"/etc/test.conf", "/etc/test2.conf"})}


def test_files_modified_all_files_are_ignored(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": [DeltaEntry("/usr/bin/bash"), DeltaEntry("/usr/bin/zsh")]}):
        result = files_modified(store, from_index=0, to_index=1, only_ignored=False)
        assert result == {"root": FilesModified(pre_files=set(), post_files=set())}


def test_files_modified_only_show_ignored(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta(
        {"root": [DeltaEntry("/usr/bin/bash"), DeltaEntry("/usr/bin/zsh"), DeltaEntry("/etc/test.conf")]}
    ):
        result = files_modified(store, from_index=0, to_index=1, only_ignored=True)
        assert result == {"root": FilesModified(pre_files=set(), post_files={"/usr/bin/bash", "/usr/bin/zsh"})}


def test_files_modified_action_created(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": [DeltaEntry("/etc/fstab", FileChangeAction.created)]}):
        result = files_modified(store, from_index=0, to_index=1, only_ignored=False)
        assert result == {"root": FilesModified(pre_files=set(), post_files={"/etc/fstab"})}


def test_files_modified_action_deleted(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": [DeltaEntry("/etc/fstab", FileChangeAction.deleted)]}):
        result = files_modified(store, from_index=0, to_index=1, only_ignored=False)
        assert result == {"root": FilesModified(pre_files={"/etc/fstab"}, post_files=set())}


def test_files_modified_action_modified(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": [DeltaEntry("/etc/fstab", FileChangeAction.modified)]}):
        result = files_modified(store, from_index=0, to_index=1, only_ignored=False)
        assert result == {"root": FilesModified(pre_files={"/etc/fstab"}, post_files={"/etc/fstab"})}


def test_files_modified_action_type_changed(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": [DeltaEntry("/etc/fstab", FileChangeAction.type_changed)]}):
        result = files_modified(store, from_index=0, to_index=1, only_ignored=False)
        assert result == {"root": FilesModified(pre_files={"/etc/fstab"}, post_files={"/etc/fstab"})}


def test_files_modified_action_no_change(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": [DeltaEntry("/etc/fstab", FileChangeAction.no_change)]}):
        result = files_modified(store, from_index=0, to_index=1, only_ignored=False)
        assert result == {"root": FilesModified(pre_files=set(), post_files=set())}


@pytest.fixture
def mock_proot() -> Generator[MagicMock, None, None]:
    def side_effect(cmd: list[str], *args: Any, **kwargs: Any) -> list[str]:
        return cmd

    with patch("dfu.snapshots.changes.proot", side_effect=side_effect) as mock_proot:
        yield mock_proot


@pytest.fixture
def mock_subprocess_run(tmp_path: Path, mock_proot: MagicMock) -> Generator[MagicMock, None, None]:
    real_subprocess_run = subprocess.run

    def side_effect(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        new_kwargs = kwargs.copy() | {"cwd": tmp_path}
        return real_subprocess_run(cmd, *args, **new_kwargs)

    with patch("subprocess.run", side_effect=side_effect) as mock_subprocess_run:
        yield mock_subprocess_run


def test_filter_files(tmp_path: Path, store: Store, mock_subprocess_run: MagicMock) -> None:
    files: list[Path] = [
        (tmp_path / "file.txt"),
        (tmp_path / "etc" / "file2.txt"),
        (tmp_path / "very" / "nested" / "file3.txt"),
    ]
    for file in files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()

    symlink = tmp_path / "very" / "nested" / "symlink"
    symlink.parent.mkdir(parents=True, exist_ok=True)
    symlink.symlink_to(files[0])

    directory_symlink = tmp_path / "very_symlink"
    directory_symlink.symlink_to(tmp_path / "very")

    paths = [
        "etc/file2.txt",
        "very/nested/file3.txt",
        "very/nested/symlink",
        "very_symlink",
        "missing.txt",
        "etc",
        "very/nested",
        "file.txt",  # This is last on purpose, to test that the last file is read
    ]

    assert filter_files(store, MappingProxyType({SnapperName("root"): 1}), set()) == set()

    assert filter_files(store, MappingProxyType({SnapperName("root"): 1}), set(paths)) == {
        "etc/file2.txt",
        "very/nested/file3.txt",
        "very/nested/symlink",
        "very_symlink",
        "file.txt",
    }


@pytest.fixture
def mock_stat() -> Generator[Any, None, None]:
    # Store the original subprocess.run
    original_subprocess_run = subprocess.run

    def mock_subprocess_run(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        if len(cmd) >= 2 and cmd[0] == "sudo" and cmd[1] == "stat":
            # Strip off sudo and call the real stat command
            real_cmd = ["stat"] + cmd[2:]
            result = original_subprocess_run(real_cmd, *args, **kwargs)
            return result
        else:
            # For other commands, throw an exception
            raise ValueError(f"Unexpected subprocess.run call: {cmd}")

    with patch("subprocess.run", side_effect=mock_subprocess_run):
        yield mock_subprocess_run


@pytest.fixture
def mock_snapper(tmp_path: Path) -> Generator[Any, None, None]:
    root_path = tmp_path / "root" / "snapshot"
    user_path = tmp_path / "user" / "snapshot"
    root_path.mkdir(parents=True)
    user_path.mkdir(parents=True)

    with (
        patch.object(Snapper, "get_mountpoint", autospec=True) as mock_get_mountpoint,
        patch.object(Snapper, "get_snapshot_path", autospec=True) as mock_get_snapshot_path,
    ):

        def get_mountpoint_side_effect(self: Snapper) -> Path:
            return Path("/" + self.snapper_name)

        def get_snapshot_path_side_effect(self: Snapper, snapshot_id: int) -> Path:
            return tmp_path / self.snapper_name / "snapshot"

        mock_get_mountpoint.side_effect = get_mountpoint_side_effect
        mock_get_snapshot_path.side_effect = get_snapshot_path_side_effect

        yield mock_get_snapshot_path


def test_get_permissions_no_changes(store: Store, mock_filter_files: MagicMock) -> None:
    result = get_permissions(store, files_modified={}, snapshot_index=1)
    assert len(result.entries) == 0


def test_get_permissions_empty_file_owned_by_user(
    tmp_path: Path,
    store_with_user_snapper: Store,
    mock_snapper: MagicMock,
    mock_stat: Any,
    mock_filter_files: MagicMock,
    current_user: str,
    current_group: str,
) -> None:
    (tmp_path / "user" / "snapshot" / "file.txt").touch()
    result = get_permissions(
        store_with_user_snapper, files_modified={SnapperName("user"): set(["/user/file.txt"])}, snapshot_index=1
    )
    expected_entry = AclEntry(Path("/user/file.txt"), "644", current_user, current_group)
    assert result.entries[Path("/user/file.txt")] == expected_entry


def test_get_permissions_file_owned_by_user(
    tmp_path: Path,
    store_with_user_snapper: Store,
    mock_snapper: MagicMock,
    mock_stat: Any,
    mock_filter_files: MagicMock,
    current_user: str,
    current_group: str,
) -> None:
    (tmp_path / "user" / "snapshot" / "file.txt").write_text("Hello, world!")
    result = get_permissions(
        store_with_user_snapper, files_modified={SnapperName("user"): set(["/user/file.txt"])}, snapshot_index=1
    )
    expected_entry = AclEntry(Path("/user/file.txt"), "644", current_user, current_group)
    assert result.entries[Path("/user/file.txt")] == expected_entry


def test_get_permissions_symlink_owned_by_user(
    tmp_path: Path,
    store_with_user_snapper: Store,
    mock_snapper: MagicMock,
    mock_stat: Any,
    mock_filter_files: MagicMock,
    current_user: str,
    current_group: str,
) -> None:
    real_file = tmp_path / "real_file.txt"
    real_file.write_text("Hello, world!")
    real_file.chmod(0o600)
    sym_path = tmp_path / "user" / "snapshot" / "symlink.txt"
    sym_path.symlink_to(real_file)
    # Symlinks are always 777
    result = get_permissions(
        store_with_user_snapper, files_modified={SnapperName("user"): set(["/user/symlink.txt"])}, snapshot_index=1
    )
    expected_entry = AclEntry(Path("/user/symlink.txt"), "777", current_user, current_group)
    assert result.entries[Path("/user/symlink.txt")] == expected_entry


def test_get_permission_subpath_owned_by_user(
    tmp_path: Path,
    store_with_user_snapper: Store,
    mock_snapper: MagicMock,
    mock_stat: Any,
    mock_filter_files: MagicMock,
    current_user: str,
    current_group: str,
) -> None:
    path = tmp_path / "user" / "snapshot" / "subpath" / "subpath2" / "file.txt"
    path.parent.mkdir(parents=True)
    path.parent.chmod(0o766)
    path.parent.parent.chmod(0o766)
    path.write_text("Hello, world!")
    path.chmod(0o644)
    result = get_permissions(
        store_with_user_snapper,
        files_modified={SnapperName("user"): set(["/user/subpath/subpath2/file.txt"])},
        snapshot_index=1,
    )
    expected_entries = {
        Path("/user/subpath/"): AclEntry(Path("/user/subpath/"), "766", current_user, current_group),
        Path("/user/subpath/subpath2/"): AclEntry(Path("/user/subpath/subpath2/"), "766", current_user, current_group),
        Path("/user/subpath/subpath2/file.txt"): AclEntry(
            Path("/user/subpath/subpath2/file.txt"), "644", current_user, current_group
        ),
    }
    for path, expected_entry in expected_entries.items():
        assert result.entries[path] == expected_entry


def test_get_permissions_setuid_setgid(
    tmp_path: Path,
    store_with_user_snapper: Store,
    mock_snapper: MagicMock,
    mock_stat: Any,
    mock_filter_files: MagicMock,
    current_user: str,
    current_group: str,
) -> None:
    setuid_file = tmp_path / "user" / "snapshot" / "setuid_file"
    setuid_file.write_text("setuid executable")
    setuid_file.chmod(0o4755)

    setgid_file = tmp_path / "user" / "snapshot" / "setgid_file"
    setgid_file.write_text("setgid executable")
    setgid_file.chmod(0o2755)

    setuid_setgid_file = tmp_path / "user" / "snapshot" / "setuid_setgid_file"
    setuid_setgid_file.write_text("setuid+setgid executable")
    setuid_setgid_file.chmod(0o6755)

    setgid_dir = tmp_path / "user" / "snapshot" / "setgid_dir"
    setgid_dir.mkdir()
    setgid_dir.chmod(0o2755)

    setuid_dir = tmp_path / "user" / "snapshot" / "setuid_dir"
    setuid_dir.mkdir()
    setuid_dir.chmod(0o4755)

    result = get_permissions(
        store_with_user_snapper,
        files_modified={
            SnapperName("user"): set(
                [
                    "/user/setuid_file",
                    "/user/setgid_file",
                    "/user/setuid_setgid_file",
                    "/user/setgid_dir",
                    "/user/setuid_dir",
                ]
            )
        },
        snapshot_index=1,
    )

    expected_entries = {
        Path("/user/setgid_dir/"): AclEntry(Path("/user/setgid_dir/"), "2755", current_user, current_group),
        Path("/user/setgid_file"): AclEntry(Path("/user/setgid_file"), "2755", current_user, current_group),
        Path("/user/setuid_dir/"): AclEntry(Path("/user/setuid_dir/"), "4755", current_user, current_group),
        Path("/user/setuid_file"): AclEntry(Path("/user/setuid_file"), "4755", current_user, current_group),
        Path("/user/setuid_setgid_file"): AclEntry(
            Path("/user/setuid_setgid_file"), "6755", current_user, current_group
        ),
    }

    for path, expected_entry in expected_entries.items():
        assert result.entries[path] == expected_entry


def test_get_permissions_multiple_roots(
    tmp_path: Path,
    store_with_user_snapper: Store,
    mock_snapper: MagicMock,
    mock_stat: Any,
    mock_filter_files: MagicMock,
    current_user: str,
    current_group: str,
) -> None:
    test_file = tmp_path / "root" / "snapshot" / "subpath" / "test.txt"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("Hello, world!")
    test_file.chmod(0o644)

    user_path = tmp_path / "user" / "snapshot" / "subpath" / "test.txt"
    user_path.parent.mkdir(parents=True)
    user_path.write_text("Hello, world!")
    user_path.chmod(0o600)

    result = get_permissions(
        store_with_user_snapper,
        files_modified={
            SnapperName("root"): set(["/root/subpath/test.txt"]),
            SnapperName("user"): set(["/user/subpath/test.txt"]),
        },
        snapshot_index=1,
    )
    expected_entries = {
        Path("/root/subpath/"): AclEntry(Path("/root/subpath/"), "755", current_user, current_group),
        Path("/root/subpath/test.txt"): AclEntry(Path("/root/subpath/test.txt"), "644", current_user, current_group),
        Path("/user/subpath/"): AclEntry(Path("/user/subpath/"), "755", current_user, current_group),
        Path("/user/subpath/test.txt"): AclEntry(Path("/user/subpath/test.txt"), "600", current_user, current_group),
    }
    for path, expected_entry in expected_entries.items():
        assert result.entries[path] == expected_entry
