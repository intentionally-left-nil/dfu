from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Tuple, TypedDict, Unpack

from dfu.helpers.json_serializable import JsonSerializableMixin


class UpdateArgs(TypedDict, total=False):
    description: str | None
    snapshots: list[dict[str, int]]
    programs_added: Tuple[str, ...]
    programs_removed: Tuple[str, ...]
    version: str


@dataclass(frozen=True)
class PackageConfig(JsonSerializableMixin):
    name: str
    description: str | None
    snapshots: list[dict[str, int]] = field(default_factory=list)
    programs_added: Tuple[str, ...] = field(default_factory=tuple)
    programs_removed: Tuple[str, ...] = field(default_factory=tuple)
    version: str = "0.0.1"

    def update(self, **kwargs: Unpack[UpdateArgs]) -> 'PackageConfig':
        return replace(self, **kwargs)


def find_package_config(path: Path) -> Path | None:
    while True:
        dfu_config = path / 'dfu_config.json'
        if dfu_config.is_file():
            return dfu_config
        elif path.parent == path or path.is_mount():  # Stop at the root or a filesystem boundary
            return None
        else:
            path = path.parent  # Move up to the parent directory
