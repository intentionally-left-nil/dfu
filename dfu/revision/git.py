import subprocess
from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig


def git_init(config: Config, package_config: PackageConfig):
    package_dir = _ensure_package_dir(config, package_config)
    subprocess.run(['git', 'init'], cwd=package_dir, check=True)


def git_commit(config: Config, package_config: PackageConfig, message: str):
    package_dir = _ensure_package_dir(config, package_config)
    subprocess.run(['git', 'add', '.'], cwd=package_dir, check=True)
    subprocess.run(['git', 'commit', '-m', message], cwd=package_dir, check=True)


def ensure_global_gitignore(config: Config):
    root_dir = config.get_package_dir()
    root_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    (root_dir / '.gitignore').touch(mode=0o644)


def symlink_global_gitignore(config: Config, package_config: PackageConfig):
    package_dir = _ensure_package_dir(config, package_config)
    global_gitignore = config.get_package_dir() / '.gitignore'
    package_gitignore = package_dir / '.gitignore'
    if not package_gitignore.exists():
        package_gitignore.symlink_to(global_gitignore)


def _ensure_package_dir(config: Config, package_config: PackageConfig) -> Path:
    package_dir = config.get_package_dir() / package_config.name
    package_dir.mkdir(mode=0o755, parents=True, exist_ok=True)
    return package_dir
