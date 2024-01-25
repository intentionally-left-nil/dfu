from dataclasses import dataclass, replace
from typing import TypedDict, Unpack

from dfu.helpers.json_serializable import JsonSerializableMixin


class UpdateArgs(TypedDict, total=False):
    installed_dependencies: bool
    dry_run_dir: str | None
    patches_to_apply: list[str] | None
    copied_files: bool


@dataclass(frozen=True)
class Install(JsonSerializableMixin):
    installed_dependencies: bool = False
    dry_run_dir: str | None = None
    patches_to_apply: list[str] | None = None
    copied_files: bool = False

    def update(self, **kwargs: Unpack[UpdateArgs]) -> 'Install':
        return replace(self, **kwargs)
