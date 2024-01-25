from dataclasses import dataclass, replace
from typing import TypedDict, Unpack

from dfu.helpers.json_serializable import JsonSerializableMixin


class UpdateArgs(TypedDict, total=False):
    removed_dependencies: bool
    dry_run_dir: str | None
    copied_files: bool


@dataclass(frozen=True)
class Uninstall(JsonSerializableMixin):
    removed_dependencies: bool = False
    dry_run_dir: str | None = None
    copied_files: bool = False

    def update(self, **kwargs: Unpack[UpdateArgs]) -> 'Uninstall':
        return replace(self, **kwargs)