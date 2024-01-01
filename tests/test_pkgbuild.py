from difflib import unified_diff

import pytest

from dfu.distribution.pkgbuild import to_pkgbuild
from dfu.package.package_config import PackageConfig


@pytest.fixture()
def patch() -> str:
    diff = unified_diff(["\n"], ["hello\n"], fromfile='a/files/etc/myfile', tofile='b/files/etc/myfile')
    return "".join(diff)


def test_to_pkgbuild_no_patch_file():
    package_config = PackageConfig(
        name="test", description="my cool description", programs_added=["test1", "test2"], version="0.0.2"
    )
    actual = to_pkgbuild(package_config, patch=None)
    expected = """\
pkgname='test'
pkgver='0.0.2'
pkgrel=1
pkgdesc='my cool description'
arch=('any')
license=('MIT')
depends=(test1 test2)
source=()

sha256sums=()
"""
    assert actual == expected


def test_to_pkgbuild(patch: str):
    package_config = PackageConfig(
        name="test", description="my cool description", programs_added=["test1", "test2"], version="0.0.2"
    )

    actual = to_pkgbuild(package_config, patch=patch)
    expected = """\
pkgname='test'
pkgver='0.0.2'
pkgrel=1
pkgdesc='my cool description'
arch=('any')
license=('MIT')
depends=(test1 test2)
source=(changes.patch)

prepare() {
    cp "/etc/myfile" "${srcdir}/files/etc/myfile"
}

build() {
    cd "${srcdir}"
    patch -p1 < changes.patch
}

package() {
    cp -r "${srcdir}/files" "${pkgdir}/"
}

sha256sums=(6dae9b0edff4832474dd916f3ab0f115663f3cad095f35b16124862f37c0fd37)
"""
    assert actual == expected
