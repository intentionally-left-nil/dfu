from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig
from dfu.revision.git import copy_template_gitignore, git_add, git_commit, git_init


def create_package(name: str, description: str | None = None) -> Path:
    package = PackageConfig(name=name, description=description)
    package_dir = Path(".")
    config_path = package_dir / 'dfu_config.json'

    git_init(package_dir)
    copy_template_gitignore(package_dir)
    package.write(config_path)
    git_add(package_dir, ['.gitignore', 'dfu_config.json'])
    git_commit(package_dir, 'Initial commit')
    return config_path
