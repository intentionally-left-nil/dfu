from dataclasses import dataclass
import tomllib
from typing import Union
import os
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
    def from_file(cls, path: Union[os.PathLike, str]) -> "Config":
        with open(path, 'r') as f:
            return cls.from_toml(f.read())

    @classmethod
    def from_toml(cls, toml: str) -> "Config":
        data = tomllib.loads(toml)
        return fromdict(cls, data)
