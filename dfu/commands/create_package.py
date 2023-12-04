from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig
from dfu.package.version_number import get_version_number


def create_package(config: Config, name: str, description: str | None = None) -> Path:
    package = PackageConfig(name=name, description=description)
    version_number = str(get_version_number(config)).zfill(5)
    package_name = Path(config.package_dir) / f"{version_number}_{name}" / "dfu_config.json"
    package_name.parent.mkdir(parents=True, exist_ok=False)
    package.write(package_name)
    return package_name
