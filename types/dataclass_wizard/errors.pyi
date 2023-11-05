from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import Field as Field
from typing import Any

from _typeshed import Incomplete

JSONObject = dict[str, Any]

class JSONWizardError(ABC, Exception):
    @property
    @abstractmethod
    def message(self) -> str: ...

class ParseError(JSONWizardError):
    obj: Incomplete
    obj_type: Incomplete
    ann_type: Incomplete
    base_error: Incomplete
    kwargs: Incomplete
    def __init__(
        self,
        base_err: Exception,
        obj: Any,
        ann_type: type | Iterable,
        _default_class: type | None = ...,
        _field_name: str | None = ...,
        _json_object: Any = ...,
        **kwargs,
    ) -> None: ...
    @property
    def class_name(self) -> str | None: ...
    @class_name.setter
    def class_name(self, cls: type | None): ...
    @property
    def field_name(self) -> str | None: ...
    @field_name.setter
    def field_name(self, name: str | None): ...
    @property
    def json_object(self): ...
    @json_object.setter
    def json_object(self, json_obj) -> None: ...
    @staticmethod
    def name(obj) -> str: ...
    @property
    def message(self) -> str: ...

class MissingFields(JSONWizardError):  # noqa: N818
    obj: Incomplete
    fields: Incomplete
    missing_fields: Incomplete
    base_error: Incomplete
    kwargs: Incomplete
    class_name: Incomplete
    def __init__(
        self,
        base_err: Exception,
        obj: JSONObject,
        cls: type,
        cls_kwargs: JSONObject,
        cls_fields: tuple[Field],
        **kwargs,
    ) -> None: ...
    @staticmethod
    def name(obj) -> str: ...
    @property
    def message(self) -> str: ...

class UnknownJSONKey(JSONWizardError):  # noqa: N818
    json_key: Incomplete
    obj: Incomplete
    fields: Incomplete
    kwargs: Incomplete
    class_name: Incomplete
    def __init__(self, json_key: str, obj: JSONObject, cls: type, cls_fields: tuple[Field], **kwargs) -> None: ...
    @staticmethod
    def name(obj) -> str: ...
    @property
    def message(self) -> str: ...

class MissingData(ParseError):  # noqa: N818
    nested_class_name: Incomplete
    def __init__(self, nested_cls: type, **kwargs) -> None: ...
    @staticmethod
    def name(obj) -> str: ...
    @property
    def message(self) -> str: ...
