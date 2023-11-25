import tempfile
import tomllib

import dataclass_wizard.errors
import pytest

from dfu.config import Btrfs, Config


def test_valid_config():
    toml = """
package_dir = "/path/to/package_dir"
[btrfs]
snapper_configs = ["/home", "/"]
"""
    actual = Config.from_toml(toml)
    expected = Config(
        package_dir="/path/to/package_dir",
        btrfs=Btrfs(snapper_configs=["/home", "/"]),
    )
    assert actual == expected


def test_from_file():
    toml = """
package_dir = "/path/to/package_dir"
[btrfs]
snapper_configs = ["/home"]
"""
    with tempfile.NamedTemporaryFile("w") as f:
        f.write(toml)
        f.flush()
        actual = Config.from_file(f.name)
        expected = Config(package_dir="/path/to/package_dir", btrfs=Btrfs(snapper_configs=["/home"]))
        assert actual == expected


def test_invalid_types():
    toml = """
package_dir = "/path/to/package_dir"
[btrfs]
snapper_configs = 5
"""
    with pytest.raises(dataclass_wizard.errors.ParseError):
        Config.from_toml(toml)


def test_missing_field():
    toml = """
package_dir = "/path/to/package_dir"
[[btrfs.mounts]]
    src = "/home"
"""
    with pytest.raises(dataclass_wizard.errors.MissingFields):
        Config.from_toml(toml)


def test_invalid_toml():
    toml = """{]"""
    with pytest.raises(tomllib.TOMLDecodeError):
        Config.from_toml(toml)
