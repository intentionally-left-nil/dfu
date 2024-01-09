from dataclasses import dataclass, replace
from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig


@dataclass(frozen=True)
class State:
    config: Config
    package_dir: Path
    package_config: PackageConfig

    def update(self, **kwargs) -> 'State':
        return replace(self, **kwargs)
