from typing import Any, TypeVar

T = TypeVar("T")
JSONObject = dict[str, Any]

def fromdict(cls: type[T], d: JSONObject) -> T: ...
