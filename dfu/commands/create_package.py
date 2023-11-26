from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig, State
from dfu.package.version_number import get_version_number


def create_package(config: Config, name: str, description: str | None = None) -> Path:
    package = PackageConfig(name=name, description=description, state=State.new)
    version_number = get_version_number(config)
    version_number = str(version_number).zfill(5)
    package_name = Path(config.package_dir) / f"{version_number}_{name}" / "dfu_config.json"
    package_name.mkdir(parents=True, exist_ok=False)
    package.write(package_name)
    return package_name
