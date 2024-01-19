import json
from pathlib import Path
from typing import Type, TypeVar

import msgspec

T = TypeVar('T', bound='JsonSerializableMixin')


class JsonSerializableMixin:
    @classmethod
    def from_file(cls: Type[T], path: Path) -> T:
        with open(path) as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls: Type[T], data: str) -> T:
        return msgspec.json.decode(data, type=cls)

    def write(self, path: Path, mode: str = "wb"):
        if 'b' not in mode:
            mode += 'b'
        data = msgspec.json.encode(self)
        with open(path, mode) as f:
            f.write(data)
