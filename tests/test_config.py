import tempfile

import pytest
from msgspec import DecodeError, ValidationError

from dfu.config import Btrfs, Config
from dfu.snapshots.snapper import SnapperName


def test_valid_config() -> None:
    toml = """
package_dir = "/path/to/package_dir"
[btrfs]
snapper_configs = ["/home", "/"]
"""
    actual = Config.from_toml(toml)
    expected = Config(
        btrfs=Btrfs(snapper_configs=(SnapperName("/home"), SnapperName("/"))),
    )
    assert actual == expected


def test_default_package_dir() -> None:
    toml = """
[btrfs]
snapper_configs = ["/home", "/"]
"""
    actual = Config.from_toml(toml)
    expected = Config(btrfs=Btrfs(snapper_configs=(SnapperName("/home"), SnapperName("/"))))
    assert actual == expected


def test_from_file() -> None:
    toml = """
package_dir = "/path/to/package_dir"
[btrfs]
snapper_configs = ["/home"]
"""
    with tempfile.NamedTemporaryFile("w") as f:
        f.write(toml)
        f.flush()
        actual = Config.from_file(f.name)
        expected = Config(btrfs=Btrfs(snapper_configs=(SnapperName("/home"),)))
        assert actual == expected


def test_invalid_types() -> None:
    toml = """
package_dir = "/path/to/package_dir"
[btrfs]
snapper_configs = 5
"""
    with pytest.raises(ValidationError):
        Config.from_toml(toml)


def test_missing_field() -> None:
    toml = """
package_dir = "/path/to/package_dir"
[[btrfs.mounts]]
    src = "/home"
"""
    with pytest.raises(ValidationError):
        Config.from_toml(toml)


def test_invalid_toml() -> None:
    toml = """{]"""
    with pytest.raises(DecodeError):
        Config.from_toml(toml)
