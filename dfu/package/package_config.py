import json
import os
from dataclasses import dataclass, field
from enum import StrEnum

from dataclass_wizard import asdict, fromdict


@dataclass
class Snapshot:
    pre_id: int
    post_id: int | None = None


SnapshotMapping = dict[str, int]


@dataclass
class PackageConfig:
    name: str
    description: str | None
    snapshots: list[dict[str, Snapshot]] = field(default_factory=list)
    programs_added: list[str] = field(default_factory=list)
    programs_removed: list[str] = field(default_factory=list)
    version: str = "0.0.1"

    def write(self, path: os.PathLike | str):
        with open(path, "w") as f:
            json.dump(asdict(self), f, indent=4)

    def snapshot_mapping(self, *, use_pre_id: bool, index: int = -1) -> SnapshotMapping:
        snapshot = self.snapshots[index]
        mapping: dict[str, int]
        if use_pre_id:
            mapping = {k: v.pre_id for k, v in snapshot.items()}
        else:
            mapping = {}
            for k, v in snapshot.items():
                if v.post_id is None:
                    raise ValueError("Post-snapshot does not exist")
                mapping[k] = v.post_id
        return mapping

    @classmethod
    def from_file(cls, path: os.PathLike | str) -> "PackageConfig":
        with open(path) as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls, data: str) -> "PackageConfig":
        return fromdict(cls, json.loads(data))
