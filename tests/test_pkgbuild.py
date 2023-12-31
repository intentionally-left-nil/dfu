import pytest

from dfu.distribution.pkgbuild import to_pkgbuild
from dfu.package.package_config import PackageConfig


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


def test_to_pkgbuild():
    package_config = PackageConfig(
        name="test", description="my cool description", programs_added=["test1", "test2"], version="0.0.2"
    )
    patch = """\
diff --git a/files/etc/myfile b/files/etc/myfile
index 51745d0..b6b08c0 100644
--- a/files/etc/myfile
+++ b/files/etc/myfile
@@ -1 +1 @@
+hello
"""
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

sha256sums=(1a5c5561fd4de8b44f96054b773eb1ddd08a6fbf41a5953f9021b2369469a942)
"""
    assert actual == expected
