from dfu.package.package_config import PackageConfig

PKGBUILD_TEMPLATE = """\
pkgname='{name}'
pkgver='{version}'
pkgrel=1
pkgdesc='{description}'
arch=('any')
license=('MIT')
depends=({dependencies})
"""


def to_pkgbuild(package_config: PackageConfig) -> str:
    return PKGBUILD_TEMPLATE.format(
        name=package_config.name,
        version=package_config.version,
        description=package_config.description,
        dependencies=" ".join(package_config.programs_added),
    )
