import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dataclass_wizard import asdict, fromdict

from dfu.helpers.json_serializable import JsonSerializableMixin


@dataclass
class Snapshot:
    pre_id: int
    post_id: int | None = None


SnapshotMapping = dict[str, int]


@dataclass
class PackageConfig(JsonSerializableMixin):
    name: str
    description: str | None
    snapshots: list[dict[str, Snapshot]] = field(default_factory=list)
    programs_added: list[str] = field(default_factory=list)
    programs_removed: list[str] = field(default_factory=list)
    version: str = "0.0.1"

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


def find_package_config(path: Path) -> Path | None:
    while True:
        dfu_config = path / 'dfu_config.json'
        if dfu_config.is_file():
            return dfu_config
        elif path.parent == path or path.is_mount():  # Stop at the root or a filesystem boundary
            return None
        else:
            path = path.parent  # Move up to the parent directory
