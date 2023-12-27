import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest

from dfu.config import Btrfs, Config
from dfu.package.package_config import PackageConfig
from dfu.revision.git import (
    ensure_global_gitignore,
    git_commit,
    git_init,
    symlink_global_gitignore,
)


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    with TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def config(temp_dir) -> Config:
    return Config(btrfs=Btrfs(snapper_configs=[]), package_dir=temp_dir)


@pytest.fixture
def package_config() -> PackageConfig:
    return PackageConfig(name='my_package', description=None)


def test_git_init(temp_dir: Path, config: Config, package_config: PackageConfig):
    git_init(config, package_config)
    assert (temp_dir / 'my_package' / '.git').exists()


def test_git_commit(temp_dir: Path, config: Config, package_config: PackageConfig):
    git_init(config, package_config)
    (temp_dir / package_config.name / 'file.txt').touch()
    git_commit(config, package_config, 'Initial commit')
    result = subprocess.run(
        ['git', 'show', '--name-only', '--oneline', 'HEAD'],
        cwd=temp_dir / package_config.name,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert result.stdout.splitlines()[1:] == ["file.txt"]


def test_ensure_global_gitignore(temp_dir: Path, config: Config):
    ensure_global_gitignore(config)
    assert (temp_dir / '.gitignore').exists()


def test_ensure_global_gitignore_already_exists(temp_dir: Path, config: Config):
    (temp_dir / '.gitignore').write_text('hello')
    ensure_global_gitignore(config)
    assert (temp_dir / '.gitignore').read_text() == 'hello'


def test_symlink_global_gitignore(temp_dir: Path, config: Config, package_config: PackageConfig):
    ensure_global_gitignore(config)
    symlink_global_gitignore(config, package_config)
    assert (temp_dir / package_config.name / '.gitignore').exists()
    assert (temp_dir / package_config.name / '.gitignore').is_symlink()
    assert (temp_dir / package_config.name / '.gitignore').resolve() == (temp_dir / '.gitignore').resolve()


def test_symlink_global_gitignore_already_exists(temp_dir: Path, config: Config, package_config: PackageConfig):
    ensure_global_gitignore(config)
    (temp_dir / package_config.name).mkdir(parents=True, exist_ok=True)
    (temp_dir / package_config.name / '.gitignore').write_text('hello')
    symlink_global_gitignore(config, package_config)
    assert (temp_dir / package_config.name / '.gitignore').read_text() == 'hello'
