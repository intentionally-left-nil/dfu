from io import StringIO
from typing import Iterable, Optional, TypeVar, Union

from unidiff.constants import DEFAULT_ENCODING as DEFAULT_ENCODING
from unidiff.constants import DEV_NULL as DEV_NULL
from unidiff.constants import LINE_TYPE_ADDED as LINE_TYPE_ADDED
from unidiff.constants import LINE_TYPE_CONTEXT as LINE_TYPE_CONTEXT
from unidiff.constants import LINE_TYPE_EMPTY as LINE_TYPE_EMPTY
from unidiff.constants import LINE_TYPE_NO_NEWLINE as LINE_TYPE_NO_NEWLINE
from unidiff.constants import LINE_TYPE_REMOVED as LINE_TYPE_REMOVED
from unidiff.constants import LINE_VALUE_NO_NEWLINE as LINE_VALUE_NO_NEWLINE
from unidiff.constants import RE_BINARY_DIFF as RE_BINARY_DIFF
from unidiff.constants import RE_DIFF_GIT_DELETED_FILE as RE_DIFF_GIT_DELETED_FILE
from unidiff.constants import RE_DIFF_GIT_HEADER as RE_DIFF_GIT_HEADER
from unidiff.constants import (
    RE_DIFF_GIT_HEADER_NO_PREFIX as RE_DIFF_GIT_HEADER_NO_PREFIX,
)
from unidiff.constants import RE_DIFF_GIT_HEADER_URI_LIKE as RE_DIFF_GIT_HEADER_URI_LIKE
from unidiff.constants import RE_DIFF_GIT_NEW_FILE as RE_DIFF_GIT_NEW_FILE
from unidiff.constants import RE_HUNK_BODY_LINE as RE_HUNK_BODY_LINE
from unidiff.constants import RE_HUNK_EMPTY_BODY_LINE as RE_HUNK_EMPTY_BODY_LINE
from unidiff.constants import RE_HUNK_HEADER as RE_HUNK_HEADER
from unidiff.constants import RE_NO_NEWLINE_MARKER as RE_NO_NEWLINE_MARKER
from unidiff.constants import RE_SOURCE_FILENAME as RE_SOURCE_FILENAME
from unidiff.constants import RE_TARGET_FILENAME as RE_TARGET_FILENAME
from unidiff.errors import UnidiffParseError as UnidiffParseError

class Line:
    source_line_no: Optional[int]
    target_line_no: Optional[int]
    diff_line_no: Optional[int]
    line_type: str
    value: str
    def __init__(
        self,
        value: str,
        line_type: str,
        source_line_no: Optional[int] = None,
        target_line_no: Optional[int] = None,
        diff_line_no: Optional[int] = None,
    ) -> None: ...
    def __eq__(self, other: object) -> bool: ...
    @property
    def is_added(self) -> bool: ...
    @property
    def is_removed(self) -> bool: ...
    @property
    def is_context(self) -> bool: ...

class PatchInfo(list): ...

class Hunk(list):
    source_start: int
    source_length: int
    target_start: int
    target_length: int
    section_header: str
    def __init__(
        self, src_start: int = 0, src_len: int = 0, tgt_start: int = 0, tgt_len: int = 0, section_header: str = ''
    ) -> None: ...
    def append(self, line: Line) -> None: ...
    @property
    def added(self) -> Optional[int]: ...
    @property
    def removed(self) -> Optional[int]: ...
    def is_valid(self) -> bool: ...
    def source_lines(self) -> Iterable[Line]: ...
    @property
    def source(self) -> Iterable[str]: ...
    def target_lines(self) -> Iterable[Line]: ...
    @property
    def target(self) -> Iterable[str]: ...

class PatchedFile(list):
    patch_info: Optional[str]
    source_file: str
    source_timestamp: Optional[str]
    target_file: Optional[str]
    target_timestamp: Optional[str]
    is_binary_file: bool
    def __init__(
        self,
        patch_info: Optional[str] = None,
        source: str = '',
        target: Optional[str] = '',
        source_timestamp: Optional[str] = None,
        target_timestamp: Optional[str] = None,
        is_binary_file: bool = False,
    ) -> None: ...
    @property
    def path(self) -> str: ...
    @property
    def added(self) -> int: ...
    @property
    def removed(self) -> int: ...
    @property
    def is_rename(self): ...
    @property
    def is_added_file(self) -> bool: ...
    @property
    def is_removed_file(self) -> bool: ...
    @property
    def is_modified_file(self) -> bool: ...

class PatchSet(list):
    def __init__(
        self, f: Union[StringIO, str], encoding: Optional[str] = None, metadata_only: bool = False
    ) -> None: ...
    @classmethod
    def from_filename(cls, filename, encoding=..., errors: Optional[str] = None, newline: Optional[str] = None): ...
    @classmethod
    def from_string(cls, data: str, encoding: Optional[str] = None, errors: Optional[str] = 'strict') -> PatchSet: ...
    @property
    def added_files(self) -> list[PatchedFile]: ...
    @property
    def removed_files(self) -> list[PatchedFile]: ...
    @property
    def modified_files(self) -> list[PatchedFile]: ...
    @property
    def added(self) -> int: ...
    @property
    def removed(self) -> int: ...
