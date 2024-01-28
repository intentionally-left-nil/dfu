from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import pytest

from dfu.api import Store
from dfu.revision.git import DEFAULT_GITIGNORE
from dfu.snapshots.changes import files_modified
from dfu.snapshots.snapper import Snapper
from dfu.snapshots.snapper_diff import FileChangeAction, SnapperDiff


@pytest.fixture
def store(tmp_path: Path, request: pytest.FixtureRequest, setup_git):
    gitignore = tmp_path / '.gitignore'
    gitignore.write_text(DEFAULT_GITIGNORE)

    base_store: Store = request.getfixturevalue('store')
    base_store.state = base_store.state.update(
        package_dir=tmp_path,
        package_config=base_store.state.package_config.update(
            snapshots=(MappingProxyType({"root": 1}), MappingProxyType({"root": 2}))
        ),
    )
    return base_store


@contextmanager
def mock_get_delta(responses: dict[str, list[str]]):
    def side_effect(self, pre_snapshot_id: int, post_snapshot_id: int) -> list[SnapperDiff]:
        response = responses[self.snapper_name]
        return [SnapperDiff(path=path, action=FileChangeAction.created, permissions_changed=False) for path in response]

    with patch.object(Snapper, 'get_delta', autospec=True) as mock_get_delta:
        mock_get_delta.side_effect = side_effect
        yield


def test_files_modified_no_snapshots(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(snapshots=(MappingProxyType({}),))
    )
    with mock_get_delta({"root": []}):
        assert files_modified(store, from_index=0, to_index=0, only_ignored=False) == set()


def test_files_modified_no_changes(store: Store):
    with mock_get_delta({"root": []}):
        assert files_modified(store, from_index=0, to_index=0, only_ignored=False) == set()


def test_files_modified_nothing_ignored(store: Store):
    with mock_get_delta({"root": ["/etc/test.conf", "/etc/test2.conf"]}):
        assert files_modified(store, from_index=0, to_index=1, only_ignored=False) == set(
            ["/etc/test.conf", "/etc/test2.conf"]
        )


def test_files_modified_all_files_are_ignored(store: Store):
    with mock_get_delta({"root": ["/usr/bin/bash", "/usr/bin/zsh"]}):
        assert files_modified(store, from_index=0, to_index=1, only_ignored=False) == set()


def test_files_modified_only_show_ignored(store: Store):
    with mock_get_delta({"root": ["/usr/bin/bash", "/usr/bin/zsh", "/etc/test.conf"]}):
        assert files_modified(store, from_index=0, to_index=1, only_ignored=True) == set(
            ["/usr/bin/bash", "/usr/bin/zsh"]
        )
