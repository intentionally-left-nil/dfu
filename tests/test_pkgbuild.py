import pytest

from dfu.distribution.pkgbuild import to_pkgbuild
from dfu.package.package_config import PackageConfig


def test_to_pkgbuild():
    package_config = PackageConfig(
        name="test", description="my cool description", programs_added=["test1", "test2"], version="0.0.2"
    )
    actual = to_pkgbuild(package_config)
    expected = """\
pkgname='test'
pkgver='0.0.2'
pkgrel=1
pkgdesc='my cool description'
arch=('any')
license=('MIT')
depends=(test1 test2)
"""
    assert actual == expected
