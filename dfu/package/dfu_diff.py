from dataclasses import dataclass, replace
from typing import TypedDict, Unpack

from dfu.helpers.json_serializable import JsonSerializableMixin


class UpdateArgs(TypedDict, total=False):
    from_index: int
    to_index: int
    working_dir: str | None
    copied_pre_files: bool
    copied_post_files: bool
    updated_installed_programs: bool
    created_patch_file: bool


@dataclass(frozen=True)
class DfuDiff(JsonSerializableMixin):
    from_index: int
    to_index: int
    working_dir: str | None = None
    copied_pre_files: bool = False
    copied_post_files: bool = False
    updated_installed_programs: bool = False
    created_patch_file: bool = False

    def update(self, **kwargs: Unpack[UpdateArgs]) -> 'DfuDiff':
        return replace(self, **kwargs)
