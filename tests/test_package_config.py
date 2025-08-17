from dataclasses import FrozenInstanceError, dataclass, field
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import msgspec
import pytest

from dfu.helpers.json_serializable import JsonSerializableMixin
from dfu.package.package_config import PackageConfig, find_package_config
from dfu.snapshots.snapper import SnapperName


@dataclass
class ValidConfigTest:
    test_id: str
    name: str = "expected_name"
    description: str | None = "expected_description"
    snapshots: tuple[MappingProxyType[SnapperName, int], ...] = field(default_factory=tuple)


valid_config_tests = [
    ValidConfigTest(test_id="empty"),
    ValidConfigTest(test_id="one snapshot", snapshots=(MappingProxyType({SnapperName("root"): 1}),)),
    ValidConfigTest(
        test_id="two snapshots",
        snapshots=(MappingProxyType({SnapperName("root"): 1}), MappingProxyType({SnapperName("root"): 2})),
    ),
    ValidConfigTest(
        test_id="one snapshot with root & home, and the second snapshot with only root",
        snapshots=(
            MappingProxyType({SnapperName("root"): 1, SnapperName("home"): 2}),
            MappingProxyType({SnapperName("root"): 3}),
        ),
    ),
    ValidConfigTest(
        test_id="two snapshots with root & home",
        snapshots=(
            MappingProxyType({SnapperName("root"): 1, SnapperName("home"): 2}),
            MappingProxyType({SnapperName("root"): 3, SnapperName("home"): 4}),
        ),
    ),
    ValidConfigTest(
        test_id="two snapshots where the directories are different",
        snapshots=(MappingProxyType({SnapperName("root"): 1}), MappingProxyType({SnapperName("home"): 2})),
    ),
    ValidConfigTest(
        test_id="Three snapshots",
        snapshots=(
            MappingProxyType({SnapperName("root"): 1}),
            MappingProxyType({SnapperName("root"): 2}),
            MappingProxyType({SnapperName("root"): 3}),
        ),
    ),
]


@pytest.mark.parametrize("test", valid_config_tests, ids=[t.test_id for t in valid_config_tests])
def test_valid_configs(test: ValidConfigTest) -> None:
    json_data = msgspec.json.encode(test, enc_hook=JsonSerializableMixin.enc_hook).decode('utf-8')
    actual = PackageConfig.from_json(json_data)
    expected = PackageConfig(name=test.name, description=test.description, snapshots=test.snapshots)
    assert actual == expected


def test_file_in_current_directory(tmp_path: Path) -> None:
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.touch()
    assert find_package_config(tmp_path) == dfu_config


def test_dfu_config_is_directory_not_file(tmp_path: Path) -> None:
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.mkdir()
    assert find_package_config(tmp_path) is None


def test_file_in_parent_directory(tmp_path: Path) -> None:
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.touch()
    child_dir = tmp_path / 'child'
    child_dir.mkdir()
    assert find_package_config(child_dir) == dfu_config


def test_file_in_grandparent_directory(tmp_path: Path) -> None:
    dfu_config = tmp_path / 'dfu_config.json'
    dfu_config.touch()
    child_dir = tmp_path / 'child' / 'grandchild'
    child_dir.mkdir(parents=True)
    assert find_package_config(child_dir) == dfu_config


def test_permissions_issue(tmp_path: Path) -> None:
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


def test_symlinks_in_parent_hierarchy(tmp_path: Path) -> None:
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


def test_symlink_infinite_loop_in_parent_hierarchy(tmp_path: Path) -> None:
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


def test_mount_point_in_hierarchy(tmp_path: Path) -> None:
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


def test_package_config_is_immutable(package_config: PackageConfig) -> None:
    package_config = package_config.update(snapshots=(MappingProxyType({SnapperName("root"): 1}),))
    with pytest.raises(FrozenInstanceError):
        package_config.name = "new_name"  # type: ignore
    with pytest.raises(FrozenInstanceError):
        package_config.description = "new_description"  # type: ignore

    with pytest.raises(TypeError):
        package_config.snapshots[0]["root"] = 5  # type: ignore

    with pytest.raises(FrozenInstanceError):
        package_config.snapshots += (MappingProxyType({"root": 2}),)  # type: ignore

    with pytest.raises(FrozenInstanceError):
        package_config.programs_added += ("test3",)  # type: ignore

    with pytest.raises(FrozenInstanceError):
        package_config.programs_removed += ("test3",)  # type: ignore
