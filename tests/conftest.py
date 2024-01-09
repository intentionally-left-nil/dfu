import pytest

from dfu.config import Config
from dfu.package.package_config import PackageConfig


@pytest.fixture
def config() -> Config:
    toml = """
package_dir = "/path/to/package_dir"
[btrfs]
snapper_configs = ["root", "home", "log"]
"""
    return Config.from_toml(toml)


@pytest.fixture
def package_config() -> PackageConfig:
    return PackageConfig(
        name="test", description="my cool description", programs_added=["test1", "test2"], version="0.0.2"
    )
