from pathlib import Path

from dfu.distribution.pkgbuild import to_pkgbuild
from dfu.package.package_config import PackageConfig


def create_distribution(package_config_path: Path):
    package_config = PackageConfig.from_file(package_config_path)
    pkgbuild = to_pkgbuild(package_config)
    dist_folder = package_config_path.parent / 'dist'
    dist_folder.mkdir(exist_ok=True)
    with open(dist_folder / 'PKGBUILD', 'w') as f:
        f.write(pkgbuild)
