import os
from itertools import chain
from pathlib import Path
from typing import Iterable

from platformdirs import PlatformDirs

from dfu.config import Config


def load_config() -> Config:
    dirs = PlatformDirs("dfu", multipath=True)
    search_paths: Iterable[Path] = chain(
        [Path("/etc/dfu")],
        reversed([Path(p) for p in dirs.site_config_dir.split(os.pathsep)]),
        reversed([Path(p) for p in dirs.user_config_dir.split(os.pathsep)]),
    )
    config_paths: list[Path] = []
    for path in search_paths:
        config_paths.extend([Path(path) / "config.toml", Path(path) / "dfu.d" / "config.toml"])

    config: Config | None = None
    for path in config_paths:
        config = _merge(config, _try_load_config(path))
    if config is None:
        raise FileNotFoundError("No config file found")
    return config


def _try_load_config(path: Path) -> Config | None:
    try:
        return Config.from_file(path)
    except FileNotFoundError:
        return None


def _merge(base_config: Config | None, override_config: Config | None) -> Config | None:
    if base_config and override_config:
        return Config(
            btrfs=override_config.btrfs or base_config.btrfs,
            package_dir=override_config.package_dir or base_config.package_dir,
        )
    return override_config or base_config
