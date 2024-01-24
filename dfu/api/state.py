from dataclasses import dataclass, replace
from pathlib import Path
from typing import TypedDict, Unpack

from dfu.config import Config
from dfu.package.dfu_diff import DfuDiff
from dfu.package.install import Install
from dfu.package.package_config import PackageConfig
from dfu.package.uninstall import Uninstall


class UpdateArgs(TypedDict, total=False):
    config: Config
    package_dir: Path
    package_config: PackageConfig
    diff: DfuDiff | None
    install: Install | None
    uninstall: Uninstall | None


@dataclass(frozen=True)
class State:
    config: Config
    package_dir: Path
    package_config: PackageConfig
    diff: DfuDiff | None = None
    install: Install | None = None
    uninstall: Uninstall | None = None

    def update(self, **kwargs: Unpack[UpdateArgs]) -> 'State':
        return replace(self, **kwargs)
