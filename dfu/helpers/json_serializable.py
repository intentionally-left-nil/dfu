import json
from dataclasses import dataclass
from pathlib import Path
from typing import Type, TypeVar

from dataclass_wizard import asdict, fromdict

T = TypeVar('T', bound='JsonSerializableMixin')


class JsonSerializableMixin:
    @classmethod
    def from_file(cls: Type[T], path: Path) -> T:
        with open(path) as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls: Type[T], data: str) -> T:
        return fromdict(cls, json.loads(data))

    def write(self, path: Path, mode: str = "w"):
        with open(path, mode) as f:
            json.dump(asdict(self), f, indent=4)
