import json
import os
from dataclasses import dataclass, field
from enum import StrEnum

from dataclass_wizard import asdict, fromdict


@dataclass
class Snapshot:
    pre_id: int | None = None
    post_id: int | None = None


@dataclass
class PackageConfig:
    name: str
    description: str | None
    snapshots: dict[str, Snapshot] = field(default_factory=dict)

    def write(self, path: os.PathLike | str):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=4)

    @classmethod
    def from_file(cls, path: os.PathLike | str) -> "PackageConfig":
        with open(path) as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls, data: str) -> "PackageConfig":
        return fromdict(cls, json.loads(data))
