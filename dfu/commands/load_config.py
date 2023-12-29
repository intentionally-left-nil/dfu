import os
import textwrap
from itertools import chain
from pathlib import Path
from typing import Iterable

import click
from platformdirs import PlatformDirs

from dfu.config import Btrfs, Config
from dfu.snapshots.btrfs import get_all_subvolumes
from dfu.snapshots.snapper import Snapper
from dfu.snapshots.sort_snapper_configs import sort_snapper_configs


def get_config_paths() -> list[Path]:
    dirs = PlatformDirs("dfu", multipath=True)
    search_paths: Iterable[Path] = chain(
        reversed([Path(p) for p in dirs.site_config_dir.split(os.pathsep)]),
        reversed([Path(p) for p in dirs.user_config_dir.split(os.pathsep)]),
    )
    config_paths: list[Path] = []
    for path in search_paths:
        config_paths.extend([Path(path) / "config.toml", Path(path) / "dfu.d" / "config.toml"])
    return config_paths


def load_config() -> Config:
    config: Config | None = None
    for path in get_config_paths():
        config = _merge(config, _try_load_config(path))
    if config is None:
        config = _get_default_config()
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
        )
    return override_config or base_config


def _get_default_config() -> Config:
    snapper_configs = sort_snapper_configs(Snapper.get_configs())
    config = Config(btrfs=Btrfs(snapper_configs=snapper_configs))
    all_subvolumes = set(get_all_subvolumes())
    snapper_subvolumes = set([str(Snapper(c).get_mountpoint()) for c in config.btrfs.snapper_configs])
    missing_subvolumes = all_subvolumes - snapper_subvolumes
    if len(missing_subvolumes) > 0:
        click.echo(
            textwrap.dedent(
                f"""A dfu config.toml file was not located, and the default configuration cannot be used.
                The default configuration includes the following snapper configs:
                {config.btrfs.snapper_configs}
                However, the following btrfs subvolumes are missing a snapper config:
                {missing_subvolumes}
                Either create a config.toml file, using dfu config init, or create snapper configs for the missing subvolumes using snapper -c config_name mountpoint
                """
            ),
            err=True,
        )
        raise FileNotFoundError("no config.toml file found")

    return config
