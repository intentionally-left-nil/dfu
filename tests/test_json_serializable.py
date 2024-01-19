import json
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType

import pytest
from msgspec import ValidationError

from dfu.helpers.json_serializable import JsonSerializableMixin


@dataclass
class Dog(JsonSerializableMixin):
    name: str
    age: int
    breed: str | None = None


def test_from_file(tmp_path: Path):
    json_data = '{"name": "Ash", "age": 3}'
    (tmp_path / "dog.json").write_text(json_data)
    assert Dog.from_file(tmp_path / "dog.json") == Dog(name="Ash", age=3)


def test_from_json():
    json_data = '{"name": "Ash", "age": 3}'
    assert Dog.from_json(json_data) == Dog(name="Ash", age=3)


def test_from_json_missing_fields():
    json_data = '{"name": "Ash"}'
    with pytest.raises(ValidationError):
        Dog.from_json(json_data)


def test_write(tmp_path: Path):
    dog = Dog(name="Ash", age=3)
    dog.write(tmp_path / "dog.json")
    assert json.loads((tmp_path / "dog.json").read_text()) == {"name": "Ash", "age": 3, "breed": None}


def test_write_exclusive(tmp_path: Path):
    dog = Dog(name="Ash", age=3)
    dog.write(tmp_path / "dog.json", mode="x")
    assert json.loads((tmp_path / "dog.json").read_text()) == {"name": "Ash", "age": 3, "breed": None}


def test_write_exclusive_fails_if_file_exists(tmp_path: Path):
    dog = Dog(name="Ash", age=3)
    (tmp_path / "dog.json").write_text("{}")
    with pytest.raises(FileExistsError):
        dog.write(tmp_path / "dog.json", mode="x")


def test_mapping_proxy(tmp_path: Path):
    @dataclass
    class Inner(JsonSerializableMixin):
        data: MappingProxyType[str, int]
        untyped: MappingProxyType

    @dataclass
    class Outer(JsonSerializableMixin):
        inner: Inner

    outer = Outer(
        inner=Inner(
            data=MappingProxyType({"a": 1, "b": 2}),
            untyped=MappingProxyType({"a": 1, "b": "not_an_int", "c": MappingProxyType({"d": "hello"})}),
        )
    )
    outer.write(tmp_path / "example.json")
    assert json.loads((tmp_path / "example.json").read_text()) == {
        "inner": {"data": {"a": 1, "b": 2}, "untyped": {"a": 1, "b": "not_an_int", "c": {"d": "hello"}}}
    }

    assert Outer.from_file(tmp_path / "example.json") == Outer(
        inner=Inner(
            data=MappingProxyType({"a": 1, "b": 2}),
            untyped=MappingProxyType({"a": 1, "b": "not_an_int", "c": MappingProxyType({"d": "hello"})}),
        )
    )
