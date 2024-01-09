from dataclasses import dataclass, replace
from pathlib import Path
from typing import TypeVar

from dfu.config import Config
from dfu.package.package_config import PackageConfig


class Sentinel:
    pass


SENTINEL = Sentinel()


T = TypeVar('T')
Replacement = T | Sentinel | None


@dataclass(frozen=True)
class State:
    config: Config | None = None
    package_dir: Path | None = None
    package_config: PackageConfig | None = None

    def update(
        self,
        config: Replacement[Config],
        package_dir: Replacement[Path] = SENTINEL,
        package_config: Replacement[PackageConfig] = SENTINEL,
    ) -> 'State':
        kwargs = {"config": config, "package_dir": package_dir, "package_config": package_config}
        kwargs = {k: v for k, v in kwargs.items() if v is not SENTINEL}
        return replace(self, **kwargs)
