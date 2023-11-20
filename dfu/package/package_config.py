import json
import os
from dataclasses import dataclass
from enum import StrEnum

from dataclass_wizard import fromdict


class State(StrEnum):
    new = 'NEW'
    snapshot_created = 'SNAPSHOT_CREATED'


@dataclass
class PackageConfig:
    name: str
    description: str | None
    state: State

    @classmethod
    def from_file(cls, path: os.PathLike | str) -> "PackageConfig":
        with open(path) as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls, data: str) -> "PackageConfig":
        return fromdict(cls, json.loads(data))
