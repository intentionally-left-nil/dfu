from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig


def create_package(config: Config, name: str, description: str | None = None) -> Path:
    package = PackageConfig(name=name, description=description)
    root_dir = config.get_package_dir()
    package_dir = root_dir / name
    config_path = package_dir / 'dfu_config.json'
    if package_dir.parent.resolve() != root_dir.resolve():
        raise ValueError(f'Package name {name} is not allowed')
    package_dir.mkdir(mode=0o755, parents=True, exist_ok=False)
    package.write(config_path)
    return config_path
