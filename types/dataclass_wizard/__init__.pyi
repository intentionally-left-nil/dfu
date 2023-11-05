from typing import Type, Any, TypeVar
T = TypeVar('T')
JSONObject = dict[str, Any]

def fromdict(cls: Type[T], d: JSONObject) -> T: ...
