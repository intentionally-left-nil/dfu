import subprocess
from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType
from typing import Any, Generator
from unittest.mock import MagicMock, patch

import pytest

from dfu.api import Store
from dfu.revision.git import DEFAULT_GITIGNORE
from dfu.snapshots.changes import files_modified, filter_files
from dfu.snapshots.proot import proot
from dfu.snapshots.snapper import Snapper, SnapperName
from dfu.snapshots.snapper_diff import FileChangeAction, SnapperDiff


@pytest.fixture
def store(tmp_path: Path, request: pytest.FixtureRequest, setup_git: None) -> Store:
    gitignore = tmp_path / '.gitignore'
    gitignore.write_text(DEFAULT_GITIGNORE)

    base_store: Store = request.getfixturevalue('store')
    base_store.state = base_store.state.update(
        package_dir=tmp_path,
        package_config=base_store.state.package_config.update(
            snapshots=(MappingProxyType({SnapperName("root"): 1}), MappingProxyType({SnapperName("root"): 2}))
        ),
    )
    return base_store


@contextmanager
def mock_get_delta(responses: dict[str, list[str]]) -> Generator[MagicMock, None, None]:
    def side_effect(self: Any, pre_snapshot_id: int, post_snapshot_id: int) -> list[SnapperDiff]:
        response = responses[self.snapper_name]
        return [SnapperDiff(path=path, action=FileChangeAction.created, permissions_changed=False) for path in response]

    with patch.object(Snapper, 'get_delta', autospec=True) as mock_get_delta:
        mock_get_delta.side_effect = side_effect
        yield mock_get_delta


@pytest.fixture
def mock_filter_files() -> Generator[MagicMock, None, None]:
    def side_effect(store: Store, snapshot: MappingProxyType[SnapperName, int], paths: list[str]) -> list[str]:
        return paths

    with patch('dfu.snapshots.changes.filter_files', side_effect=side_effect) as mock_filter_files:
        yield mock_filter_files


def test_files_modified_no_snapshots(store: Store, mock_filter_files: MagicMock) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(snapshots=(MappingProxyType({}),))
    )
    with mock_get_delta({"root": []}):
        assert files_modified(store, from_index=0, to_index=0, only_ignored=False) == {}


def test_files_modified_no_changes(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": []}):
        assert files_modified(store, from_index=0, to_index=0, only_ignored=False) == {"root": []}


def test_files_modified_nothing_ignored(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": ["/etc/test.conf", "/etc/test2.conf"]}):
        assert files_modified(store, from_index=0, to_index=1, only_ignored=False) == {
            "root": ["/etc/test.conf", "/etc/test2.conf"]
        }


def test_files_modified_all_files_are_ignored(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": ["/usr/bin/bash", "/usr/bin/zsh"]}):
        assert files_modified(store, from_index=0, to_index=1, only_ignored=False) == {"root": []}


def test_files_modified_only_show_ignored(store: Store, mock_filter_files: MagicMock) -> None:
    with mock_get_delta({"root": ["/usr/bin/bash", "/usr/bin/zsh", "/etc/test.conf"]}):
        assert files_modified(store, from_index=0, to_index=1, only_ignored=True) == {
            "root": ["/usr/bin/bash", "/usr/bin/zsh"]
        }


@pytest.fixture
def mock_proot() -> Generator[MagicMock, None, None]:
    def side_effect(cmd: list[str], *args: Any, **kwargs: Any) -> list[str]:
        return cmd

    with patch('dfu.snapshots.changes.proot', side_effect=side_effect) as mock_proot:
        yield mock_proot


@pytest.fixture
def mock_subprocess_run(tmp_path: Path, mock_proot: MagicMock) -> Generator[MagicMock, None, None]:
    real_subprocess_run = subprocess.run

    def side_effect(cmd: list[str], *args: Any, **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        new_kwargs = kwargs.copy() | {"cwd": tmp_path}
        return real_subprocess_run(cmd, *args, **new_kwargs)

    with patch('subprocess.run', side_effect=side_effect) as mock_subprocess_run:
        yield mock_subprocess_run


def test_filter_files(tmp_path: Path, store: Store, mock_subprocess_run: MagicMock) -> None:
    files: list[Path] = [
        (tmp_path / "file.txt"),
        (tmp_path / 'etc' / 'file2.txt'),
        (tmp_path / 'very' / 'nested' / 'file3.txt'),
    ]
    for file in files:
        file.parent.mkdir(parents=True, exist_ok=True)
        file.touch()

    symlink = tmp_path / 'very' / 'nested' / 'symlink'
    symlink.parent.mkdir(parents=True, exist_ok=True)
    symlink.symlink_to(files[0])

    directory_symlink = tmp_path / 'very_symlink'
    directory_symlink.symlink_to(tmp_path / 'very')

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

    assert filter_files(store, MappingProxyType({SnapperName("root"): 1}), []) == []

    assert filter_files(store, MappingProxyType({SnapperName("root"): 1}), paths) == [
        "etc/file2.txt",
        "very/nested/file3.txt",
        "very/nested/symlink",
        "very_symlink",
        "file.txt",
    ]
