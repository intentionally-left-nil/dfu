from dataclasses import dataclass, replace
from pathlib import Path
from typing import TypedDict, Unpack

from dfu.config import Config
from dfu.package.dfu_diff import DfuDiff
from dfu.package.package_config import PackageConfig


class UpdateArgs(TypedDict, total=False):
    config: Config
    package_dir: Path
    package_config: PackageConfig
    diff: DfuDiff | None


@dataclass(frozen=True)
class State:
    config: Config
    package_dir: Path
    package_config: PackageConfig
    diff: DfuDiff | None = None

    def update(self, **kwargs: Unpack[UpdateArgs]) -> 'State':
        return replace(self, **kwargs)
