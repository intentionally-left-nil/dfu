from pathlib import Path

from dfu.distribution.pkgbuild import to_pkgbuild
from dfu.package.package_config import PackageConfig


def create_distribution(package_dir: Path):
    package_config = PackageConfig.from_file(package_dir / "dfu_config.json")
    patch_file = package_dir / 'changes.patch'
    patch = patch_file.read_text() if patch_file.exists() else None
    pkgbuild = to_pkgbuild(package_config, patch)
    dist_folder = package_dir / 'dist'
    dist_folder.mkdir(mode=0o755, exist_ok=True)
    if patch_file.exists():
        (dist_folder / 'changes.patch').write_text(patch_file.read_text())

    with open(dist_folder / 'PKGBUILD', 'w') as f:
        f.write(pkgbuild)
