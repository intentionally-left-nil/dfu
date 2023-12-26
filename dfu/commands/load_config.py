from pathlib import Path

from platformdirs import PlatformDirs

from dfu.config import Config


def load_config() -> Config:
    dirs = PlatformDirs("dfu")
    paths = [p / "config.toml" for p in (dirs.site_config_path, dirs.site_config_path / "dfu.d", dirs.user_config_path)]
    config: Config | None = None
    for path in paths:
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
    if base_config is None:
        return override_config
    if override_config is None:
        return None
    return Config(
        btrfs=override_config.btrfs or base_config.btrfs,
        package_dir=override_config.package_dir or base_config.package_dir,
    )
