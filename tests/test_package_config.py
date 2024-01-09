import json
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

import pytest

from dfu.package.package_config import PackageConfig, Snapshot, find_package_config


@dataclass
class ValidConfigTest:
    test_id: str
    name: str = "expected_name"
    description: str | None = "expected_description"
    snapshots_deprecated: list[dict[str, dict]] = field(default_factory=list)


valid_config_tests = [
    ValidConfigTest(test_id="empty"),
    ValidConfigTest(test_id="one snapshot with a pre_id", snapshots_deprecated=[{"root": {"pre_id": 1}}]),
    ValidConfigTest(
        test_id="one snapshot with a pre and post id", snapshots_deprecated=[{"root": {"pre_id": 1, "post_id": 2}}]
    ),
    ValidConfigTest(
        test_id="one snapshot with two volumes, both having a pre id",
        snapshots_deprecated=[{"root": {"pre_id": 1}, "home": {"pre_id": 2}}],
    ),
    ValidConfigTest(
        test_id="one snapshot with a full root, but only a pre id for home",
        snapshots_deprecated=[{"root": {"pre_id": 1, "post_id": 2}, "home": {"pre_id": 3}}],
    ),
    ValidConfigTest(
        test_id="one snapshot with two volumes, both having a pre and post id",
        snapshots_deprecated=[{"root": {"pre_id": 1, "post_id": 2}, "home": {"pre_id": 3, "post_id": 4}}],
    ),
    ValidConfigTest(
        test_id="two snapshots_deprecated with a pre_id",
        snapshots_deprecated=[{"root": {"pre_id": 1}}, {"root": {"pre_id": 2}}],
    ),
    ValidConfigTest(
        test_id="two snapshots_deprecated where the first one is full",
        snapshots_deprecated=[{"root": {"pre_id": 1, "post_id": 2}}, {"root": {"pre_id": 3}}],
    ),
    ValidConfigTest(
        test_id="two snapshots_deprecated where the directories are different",
        snapshots_deprecated=[{"root": {"pre_id": 1, "post_id": 2}}, {"home": {"pre_id": 3, "post_id": 4}}],
    ),
]


@pytest.mark.parametrize("test", valid_config_tests, ids=[t.test_id for t in valid_config_tests])
def test_valid_configs(test: ValidConfigTest):
    json_data = json.dumps(test.__dict__)
    actual = PackageConfig.from_json(json_data)
    expected_snapshots = [
        {k: Snapshot(pre_id=v['pre_id'], post_id=v.get('post_id', None)) for k, v in item.items()}
        for item in test.snapshots_deprecated
    ]
    expected = PackageConfig(name=test.name, description=test.description, snapshots_deprecated=expected_snapshots)
    assert actual == expected


@pytest.fixture
def config() -> PackageConfig:
    return PackageConfig(
        name='expected_name',
        description='expected_description',
        snapshots_deprecated=[
            {"root": Snapshot(pre_id=1, post_id=2), "home": Snapshot(pre_id=3, post_id=4)},
            {"root": Snapshot(pre_id=5, post_id=6), "home": Snapshot(pre_id=7, post_id=8)},
        ],
    )


class TestSnapshotMapping:
    def test_raises_if_invalid_id(self):
        config = PackageConfig(name='expected_name', description='expected_description')
        with pytest.raises(IndexError):
            config.snapshot_mapping(use_pre_id=False)

    def test_returns_last_pre_id(self, config: PackageConfig):
        assert config.snapshot_mapping(use_pre_id=True) == {"root": 5, "home": 7}

    def test_returns_last_pre_id_with_index(self, config):
        assert config.snapshot_mapping(index=0, use_pre_id=True) == {"root": 1, "home": 3}

    def test_raises_if_post_id_is_none(self):
        config = PackageConfig(
            name='expected_name',
            description='expected_description',
            snapshots_deprecated=[
                {"root": Snapshot(pre_id=1), "home": Snapshot(pre_id=2)},
                {"root": Snapshot(pre_id=3), "home": Snapshot(pre_id=4)},
            ],
        )
        with pytest.raises(ValueError):
            config.snapshot_mapping(use_pre_id=False)

    def test_returns_last_post_id(self, config: PackageConfig):
        assert config.snapshot_mapping(use_pre_id=False) == {"root": 6, "home": 8}

    def test_returns_last_post_id_with_index(self, config: PackageConfig):
        assert config.snapshot_mapping(index=0, use_pre_id=False) == {"root": 2, "home": 4}


def test_file_in_current_directory(tmp_path):
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.touch()
    assert find_package_config(tmp_path) == dfu_config


def test_dfu_config_is_directory_not_file(tmp_path):
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.mkdir()
    assert find_package_config(tmp_path) is None


def test_file_in_parent_directory(tmp_path):
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.touch()
    child_dir = tmp_path / 'child'
    child_dir.mkdir()
    assert find_package_config(child_dir) == dfu_config


def test_file_in_grandparent_directory(tmp_path):
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.touch()
    child_dir = tmp_path / 'child' / 'grandchild'
    child_dir.mkdir(parents=True)
    assert find_package_config(child_dir) == dfu_config


def test_permissions_issue(tmp_path: Path):
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.touch()
    child_dir = tmp_path / 'child'
    child_dir.mkdir()
    try:
        child_dir.chmod(0o000)  # Remove read permission
        with pytest.raises(PermissionError):
            find_package_config(child_dir)
    finally:
        child_dir.chmod(0o755)


def test_symlinks_in_parent_hierarchy(tmp_path: Path):
    # Creates the following directory structure:
    # tmp_path
    # ├── child
    # │   └── dfu_config.json
    # └── symlink -> child

    child_dir = tmp_path / 'child'
    child_dir.mkdir()
    dfu_config = child_dir / 'dfu_config.json'
    dfu_config.touch()
    symlink_dir = tmp_path / 'symlink'
    symlink_dir.symlink_to(child_dir, target_is_directory=True)
    assert find_package_config(symlink_dir) == symlink_dir / 'dfu_config.json'


def test_symlink_infinite_loop_in_parent_hierarchy(tmp_path: Path):
    # Creates the following directory structure:
    # tmp_path
    # ├── child
    # │   ├── dfu_config.json
    # │   ├── infinite -> child/loop
    # │   └── loop -> child/infinite

    dfu_config = tmp_path / 'child' / 'dfu_config.json'
    dfu_config.parent.mkdir()
    dfu_config.touch()
    infinite_dir = tmp_path / 'child' / 'infinite'
    loop_dir = tmp_path / 'child' / 'loop'
    infinite_dir.symlink_to(loop_dir, target_is_directory=True)
    loop_dir.symlink_to(infinite_dir, target_is_directory=True)
    assert find_package_config(infinite_dir) == dfu_config


def test_mount_point_in_hierarchy(tmp_path):
    # Creates the following directory structure:
    # tmp_path
    # ├── dfu_config.json
    # └── mount <-- Mocked to return true for is_mount()
    #     └── child
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.touch()
    mount_dir = tmp_path / 'mount'
    mount_dir.mkdir()
    child_dir = mount_dir / 'child'
    child_dir.mkdir()

    with patch.object(Path, 'is_mount', side_effect=lambda self: self == mount_dir, autospec=True):
        assert find_package_config(child_dir) is None
