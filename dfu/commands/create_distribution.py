from pathlib import Path

from dfu.api.store import Store
from dfu.distribution.pkgbuild import to_pkgbuild
from dfu.package.package_config import PackageConfig


def create_distribution(store: Store):
    assert store.state.package_dir and store.state.package_config
    patch_file = store.state.package_dir / 'changes.patch'
    patch = patch_file.read_text() if patch_file.exists() else None
    pkgbuild = to_pkgbuild(store.state.package_config, patch)
    dist_folder = store.state.package_dir / 'dist'
    dist_folder.mkdir(mode=0o755, exist_ok=True)
    if patch_file.exists():
        (dist_folder / 'changes.patch').write_text(patch_file.read_text())

    with open(dist_folder / 'PKGBUILD', 'w') as f:
        f.write(pkgbuild)
