from dataclasses import dataclass

from dfu.helpers.json_serializable import JsonSerializableMixin


@dataclass
class DfuDiff(JsonSerializableMixin):
    from_index: int
    to_index: int
    created_placeholders: bool = False
    created_base_branch: bool = False
    created_target_branch: bool = False
    updated_installed_programs: bool = False
    created_patch_file: bool = False
