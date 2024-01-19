from pathlib import Path
from types import MappingProxyType
from typing import Any, Dict, Type, TypeVar, get_args, get_origin

import msgspec

T = TypeVar('T', bound='JsonSerializableMixin')


class JsonSerializableMixin:
    @classmethod
    def from_file(cls: Type[T], path: Path) -> T:
        with open(path) as f:
            return cls.from_json(f.read())

    @classmethod
    def from_json(cls: Type[T], data: str) -> T:
        return msgspec.json.decode(data, type=cls, dec_hook=cls.dec_hook)

    def write(self, path: Path, mode: str = "wb"):
        if 'b' not in mode:
            mode += 'b'
        data = msgspec.json.encode(self, enc_hook=self.enc_hook)
        with open(path, mode) as f:
            f.write(data)

    @classmethod
    def enc_hook(cls, obj: Any) -> Any:
        if isinstance(obj, MappingProxyType):
            return obj.copy()
        else:
            raise NotImplementedError(f"Unknown type: {type(obj)}")

    @classmethod
    def dec_hook(cls, type: Type, obj: Any) -> Any:
        if type is MappingProxyType or get_origin(type) is MappingProxyType:
            args = get_args(type)
            if len(args) == 2:
                key_type: Any = args[0]
                value_type: Any = args[1]
                sub_type = Dict[key_type, value_type]
            else:
                sub_type = dict
            return MappingProxyType(msgspec.convert(obj, sub_type))
        else:
            raise NotImplementedError(f"Unknown type: {type(obj)}")
