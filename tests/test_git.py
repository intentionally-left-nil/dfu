import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Generator

import pytest

from dfu.config import Btrfs, Config
from dfu.package.package_config import PackageConfig
from dfu.revision.git import (
    copy_global_gitignore,
    ensure_global_gitignore,
    git_commit,
    git_init,
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
    subprocess.run(['git', 'config', 'user.name', 'myself'], cwd=temp_dir / package_config.name, check=True)
    subprocess.run(['git', 'config', 'user.email', 'me@example.com'], cwd=temp_dir / package_config.name, check=True)
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


def test_copy_global_gitignore_initializes_if_empty(temp_dir: Path, config: Config, package_config: PackageConfig):
    copy_global_gitignore(config, package_config)
    assert (temp_dir / package_config.name / '.gitignore').read_text() == ''


def test_copy_global_gitignore(temp_dir: Path, config: Config, package_config: PackageConfig):
    (temp_dir / '.gitignore').write_text('hello')
    copy_global_gitignore(config, package_config)
    assert (temp_dir / package_config.name / '.gitignore').read_text() == 'hello'


def test_copy_global_gitignore_already_exists(temp_dir: Path, config: Config, package_config: PackageConfig):
    (temp_dir / '.gitignore').write_text('hello')
    (temp_dir / package_config.name).mkdir(parents=True, exist_ok=True)
    (temp_dir / package_config.name / '.gitignore').write_text('world')
    copy_global_gitignore(config, package_config)
    assert (temp_dir / package_config.name / '.gitignore').read_text() == 'world'
