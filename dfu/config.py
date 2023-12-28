import os
import tomllib
from dataclasses import dataclass

from dataclass_wizard import fromdict


@dataclass
class Btrfs:
    snapper_configs: list[str]


@dataclass
class Config:
    btrfs: Btrfs

    @classmethod
    def from_file(cls, path: os.PathLike | str) -> "Config":
        with open(path) as f:
            return cls.from_toml(f.read())

    @classmethod
    def from_toml(cls, toml: str) -> "Config":
        data = tomllib.loads(toml)
        return fromdict(cls, data)
