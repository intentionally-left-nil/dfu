import subprocess
from pathlib import Path

import pytest

from dfu.config import Config
from dfu.package.package_config import PackageConfig
from dfu.revision.git import git_init


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
        name="test", description="my cool description", programs_added=("test1", "test2"), version="0.0.2"
    )


@pytest.fixture
def setup_git(tmp_path: Path):
    git_init(tmp_path)
    subprocess.run(['git', 'config', 'user.name', 'myself'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'config', 'user.email', 'me@example.com'], cwd=tmp_path, check=True)
