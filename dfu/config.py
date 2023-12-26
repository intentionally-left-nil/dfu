import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

from dataclass_wizard import fromdict
from platformdirs import PlatformDirs


@dataclass
class Btrfs:
    snapper_configs: list[str]


@dataclass
class Config:
    btrfs: Btrfs
    package_dir: str | None = None

    @classmethod
    def from_file(cls, path: os.PathLike | str) -> "Config":
        with open(path) as f:
            return cls.from_toml(f.read())

    @classmethod
    def from_toml(cls, toml: str) -> "Config":
        data = tomllib.loads(toml)
        return fromdict(cls, data)

    def get_package_dir(self) -> Path:
        return Path(self.package_dir) if self.package_dir else PlatformDirs("dfu").user_config_path / "packages"
