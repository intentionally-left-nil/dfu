import hashlib
import re
from pathlib import Path

from unidiff import PatchedFile, PatchSet
from unidiff.constants import DEV_NULL

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

{prepare}

{build}

{package}

sha256sums=({checksums})
"""


def to_pkgbuild(package_config: PackageConfig, patch: str | None) -> str:
    sources = ["changes.patch"] if patch else []
    checksums = [hashlib.sha256(patch.encode('utf-8')).hexdigest()] if patch else []
    prepare = _generate_prepare(patch) if patch else ""
    build = _generate_build() if patch else ""
    package = _generate_package() if patch else ""

    pkgbuild = PKGBUILD_TEMPLATE.format(
        name=package_config.name,
        version=package_config.version,
        description=package_config.description,
        dependencies=" ".join(package_config.programs_added),
        sources=" ".join(sources),
        prepare=prepare,
        build=build,
        package=package,
        checksums=" ".join(checksums),
    )
    return re.sub(r'\n{3,}', '\n\n', pkgbuild)


def _generate_prepare(patch: str) -> str:
    commands = []
    files: list[PatchedFile] = PatchSet(patch, metadata_only=True)
    for file in files:
        source_path = Path(file.source_file)
        if source_path == Path(DEV_NULL) or source_path.parts[1:] == Path(DEV_NULL).parts[1:]:
            continue
        if len(source_path.parts) < 3 or source_path.parts[1] != "files":
            raise ValueError(f"Unexpected source file path: {source_path}")
        source_path = Path('/', *source_path.parts[2:])
        command = '    cp "%s" "${srcdir}/files%s"' % (source_path, source_path)
        commands.append(command)
    return '''\
prepare() {
%s
}
''' % "\n".join(
        commands
    )


def _generate_build() -> str:
    return '''\
build() {
    cd "${srcdir}"
    patch -p1 < changes.patch
}
'''


def _generate_package() -> str:
    return '''\
package() {
    find "${srcdir}/files" -maxdepth 1 -mindepth 1 -exec cp -r {} "${pkgdir}/" \\;
}
'''
