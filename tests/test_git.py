import subprocess
from pathlib import Path

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
def config(tmp_path) -> Config:
    return Config(btrfs=Btrfs(snapper_configs=[]), package_dir=tmp_path)


@pytest.fixture
def package_config() -> PackageConfig:
    return PackageConfig(name='my_package', description=None)


def test_git_init(tmp_path: Path, config: Config, package_config: PackageConfig):
    git_init(config, package_config)
    assert (tmp_path / 'my_package' / '.git').exists()


def test_git_commit(tmp_path: Path, config: Config, package_config: PackageConfig):
    git_init(config, package_config)
    (tmp_path / package_config.name / 'file.txt').touch()
    subprocess.run(['git', 'config', 'user.name', 'myself'], cwd=tmp_path / package_config.name, check=True)
    subprocess.run(['git', 'config', 'user.email', 'me@example.com'], cwd=tmp_path / package_config.name, check=True)
    git_commit(config, package_config, 'Initial commit')
    result = subprocess.run(
        ['git', 'show', '--name-only', '--oneline', 'HEAD'],
        cwd=tmp_path / package_config.name,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    assert result.stdout.splitlines()[1:] == ["file.txt"]


def test_ensure_global_gitignore(tmp_path: Path, config: Config):
    ensure_global_gitignore(config)
    assert (tmp_path / '.gitignore').exists()


def test_ensure_global_gitignore_already_exists(tmp_path: Path, config: Config):
    (tmp_path / '.gitignore').write_text('hello')
    ensure_global_gitignore(config)
    assert (tmp_path / '.gitignore').read_text() == 'hello'


def test_copy_global_gitignore_initializes_if_empty(tmp_path: Path, config: Config, package_config: PackageConfig):
    copy_global_gitignore(config, package_config)
    assert (tmp_path / package_config.name / '.gitignore').read_text() == ''


def test_copy_global_gitignore(tmp_path: Path, config: Config, package_config: PackageConfig):
    (tmp_path / '.gitignore').write_text('hello')
    copy_global_gitignore(config, package_config)
    assert (tmp_path / package_config.name / '.gitignore').read_text() == 'hello'


def test_copy_global_gitignore_already_exists(tmp_path: Path, config: Config, package_config: PackageConfig):
    (tmp_path / '.gitignore').write_text('hello')
    (tmp_path / package_config.name).mkdir(parents=True, exist_ok=True)
    (tmp_path / package_config.name / '.gitignore').write_text('world')
    copy_global_gitignore(config, package_config)
    assert (tmp_path / package_config.name / '.gitignore').read_text() == 'world'
