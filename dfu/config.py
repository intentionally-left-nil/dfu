import os
import tomllib
from dataclasses import dataclass

from dataclass_wizard import fromdict


@dataclass
class Btrfs:
    @dataclass
    class Mounts:
        src: str
        snapshot: str

    mounts: list[Mounts]


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
