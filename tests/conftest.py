import pytest

from dfu.config import Config


@pytest.fixture
def config() -> Config:
    toml = """
package_dir = "/path/to/package_dir"
[btrfs]
snapper_configs = ["root", "home", "log"]
"""
    return Config.from_toml(toml)
