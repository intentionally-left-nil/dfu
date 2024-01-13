from dataclasses import dataclass, replace
from pathlib import Path
from typing import TypedDict, Unpack

from dfu.config import Config
from dfu.package.package_config import PackageConfig


class UpdateArgs(TypedDict, total=False):
    config: Config
    package_dir: Path
    package_config: PackageConfig


@dataclass(frozen=True)
class State:
    config: Config
    package_dir: Path
    package_config: PackageConfig

    def update(self, **kwargs: Unpack[UpdateArgs]) -> 'State':
        return replace(self, **kwargs)
