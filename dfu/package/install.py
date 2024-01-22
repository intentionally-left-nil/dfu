from dataclasses import dataclass, replace
from typing import TypedDict, Unpack

from dfu.helpers.json_serializable import JsonSerializableMixin


class UpdateArgs(TypedDict, total=False):
    installed_dependencies: bool
    dry_run_dir: str | None


@dataclass(frozen=True)
class Install(JsonSerializableMixin):
    installed_dependencies: bool = False
    dry_run_dir: str | None = None

    def update(self, **kwargs: Unpack[UpdateArgs]) -> 'Install':
        return replace(self, **kwargs)
