import re
from dataclasses import dataclass
from enum import StrEnum


class FileChangeAction(StrEnum):
    created = 'CREATED'
    deleted = 'DELETED'
    modified = 'MODIFIED'
    type_changed = 'TYPE_CHANGED'
    no_change = 'NO_CHANGE'


@dataclass
class SnapperDiff:
    path: str
    action: FileChangeAction
    permissions_changed: bool

    @classmethod
    def from_status(cls, status: str) -> "SnapperDiff":
        match = re.match(r'^([+-ct.])([p.])([u.])([g.])([x.])([a.])\s(.*)$', status)
        if not match:
            raise ValueError("Invalid status format")
        action_code, permissions_code, user_code, group_code, _, _, filename = match.groups()
        action_map = {
            '+': FileChangeAction.created,
            '-': FileChangeAction.deleted,
            'c': FileChangeAction.modified,
            't': FileChangeAction.type_changed,
            '.': FileChangeAction.no_change,
        }
        action = action_map[action_code]
        permissions_changed = any(char != '.' for char in [permissions_code, user_code, group_code])
        return cls(filename, action, permissions_changed)
