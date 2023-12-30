from dataclasses import dataclass

from dfu.helpers.json_serializable import JsonSerializableMixin


@dataclass
class DfuDiff(JsonSerializableMixin):
    created_placeholders: bool = False
    updated_installed_programs: bool = False
    base_branch: str | None = None
    target_branch: str | None = None
