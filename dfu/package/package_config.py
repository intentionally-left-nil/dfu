from dataclasses import dataclass, field, replace
from pathlib import Path
from types import MappingProxyType
from typing import TypedDict, Unpack

from dfu.helpers.json_serializable import JsonSerializableMixin


class UpdateArgs(TypedDict, total=False):
    description: str | None
    snapshots: tuple[MappingProxyType[str, int], ...]
    programs_added: tuple[str, ...]
    programs_removed: tuple[str, ...]
    version: str


@dataclass(frozen=True)
class PackageConfig(JsonSerializableMixin):
    name: str
    description: str | None
    snapshots: tuple[MappingProxyType[str, int], ...] = field(default_factory=tuple)
    programs_added: tuple[str, ...] = field(default_factory=tuple)
    programs_removed: tuple[str, ...] = field(default_factory=tuple)
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
