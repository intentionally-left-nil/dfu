import hashlib

from dfu.package.package_config import PackageConfig

PKGBUILD_TEMPLATE = """\
pkgname='{name}'
pkgver='{version}'
pkgrel=1
pkgdesc='{description}'
arch=('any')
license=('MIT')
depends=({dependencies})
source=({sources})

sha256sums=({checksums})
"""


def to_pkgbuild(package_config: PackageConfig, patch: str | None) -> str:
    sources = ["changes.patch"] if patch else []
    checksums = [hashlib.sha256(patch.encode('utf-8')).hexdigest()] if patch else []

    return PKGBUILD_TEMPLATE.format(
        name=package_config.name,
        version=package_config.version,
        description=package_config.description,
        dependencies=" ".join(package_config.programs_added),
        sources=" ".join(sources),
        checksums=" ".join(checksums),
    )
