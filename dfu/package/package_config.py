import json
import os
from dataclasses import dataclass, field
from enum import StrEnum

from dataclass_wizard import fromdict


@dataclass
class Snapshot:
    pre_id: int | None = None
    post_id: int | None = None


class State(StrEnum):
    new = 'NEW'
    pre_snapshot_created = 'PRE_SNAPSHOT_CREATED'
    post_snapshot_created = 'POST_SNAPSHOT_CREATED'


@dataclass
class PackageConfig:
    name: str
    description: str | None
    state: State
    snapshots: dict[str, Snapshot] = field(default_factory=dict)

    @classmethod
    def from_file(cls, path: os.PathLike | str) -> "PackageConfig":
        with open(path) as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls, data: str) -> "PackageConfig":
        return fromdict(cls, json.loads(data))
