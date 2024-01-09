from dataclasses import dataclass

from dfu.helpers.json_serializable import JsonSerializableMixin


@dataclass
class DfuDiff(JsonSerializableMixin):
    from_index: int
    to_index: int
    created_placeholders: bool = False
    updated_installed_programs: bool = False
    created_patch_file: bool = False
    base_branch: str | None = None
    target_branch: str | None = None
