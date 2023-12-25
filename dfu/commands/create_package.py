from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig


def create_package(config: Config, name: str, description: str | None = None) -> Path:
    package = PackageConfig(name=name, description=description)
    package_name = Path(config.package_dir) / name / "dfu_config.json"
    package_name.parent.mkdir(parents=True, exist_ok=False)
    package.write(package_name)
    return package_name
