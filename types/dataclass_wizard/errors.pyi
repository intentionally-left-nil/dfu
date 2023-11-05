from _typeshed import Incomplete
from abc import ABC, abstractmethod
from dataclasses import Field as Field
from typing import Any, Dict, Iterable, Optional, Tuple, Type, Union

JSONObject = Dict[str, Any]

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
    def __init__(self, base_err: Exception, obj: Any, ann_type: Union[Type, Iterable], _default_class: Optional[type] = ..., _field_name: Optional[str] = ..., _json_object: Any = ..., **kwargs) -> None: ...
    @property
    def class_name(self) -> Optional[str]: ...
    @class_name.setter
    def class_name(self, cls: Optional[Type]): ...
    @property
    def field_name(self) -> Optional[str]: ...
    @field_name.setter
    def field_name(self, name: Optional[str]): ...
    @property
    def json_object(self): ...
    @json_object.setter
    def json_object(self, json_obj) -> None: ...
    @staticmethod
    def name(obj) -> str: ...
    @property
    def message(self) -> str: ...

class MissingFields(JSONWizardError):
    obj: Incomplete
    fields: Incomplete
    missing_fields: Incomplete
    base_error: Incomplete
    kwargs: Incomplete
    class_name: Incomplete
    def __init__(self, base_err: Exception, obj: JSONObject, cls: Type, cls_kwargs: JSONObject, cls_fields: Tuple[Field], **kwargs) -> None: ...
    @staticmethod
    def name(obj) -> str: ...
    @property
    def message(self) -> str: ...

class UnknownJSONKey(JSONWizardError):
    json_key: Incomplete
    obj: Incomplete
    fields: Incomplete
    kwargs: Incomplete
    class_name: Incomplete
    def __init__(self, json_key: str, obj: JSONObject, cls: Type, cls_fields: Tuple[Field], **kwargs) -> None: ...
    @staticmethod
    def name(obj) -> str: ...
    @property
    def message(self) -> str: ...

class MissingData(ParseError):
    nested_class_name: Incomplete
    def __init__(self, nested_cls: Type, **kwargs) -> None: ...
    @staticmethod
    def name(obj) -> str: ...
    @property
    def message(self) -> str: ...
