import os
from dataclasses import dataclass

import msgspec


@dataclass
class Btrfs:
    snapper_configs: tuple[str, ...]


@dataclass
class Config:
    btrfs: Btrfs

    @classmethod
    def from_file(cls, path: os.PathLike | str) -> "Config":
        with open(path) as f:
            return cls.from_toml(f.read())

    @classmethod
    def from_toml(cls, toml: str) -> "Config":
        return msgspec.toml.decode(toml, type=cls)
