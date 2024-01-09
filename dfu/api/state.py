from dataclasses import dataclass, replace
from pathlib import Path

from dfu.config import Config
from dfu.package.package_config import PackageConfig


@dataclass(frozen=True)
class State:
    config: Config | None = None
    package_dir: Path | None = None
    package_config: PackageConfig | None = None

    def update(self, **kwargs) -> 'State':
        return replace(self, **kwargs)
