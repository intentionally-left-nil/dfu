from dataclasses import dataclass
from pathlib import Path
from typing import override

from dfu.helpers.json_serializable import JsonSerializableMixin


@dataclass(frozen=True)
class PatchConfig(JsonSerializableMixin):
    """Configuration for a patch file containing pack metadata."""

    pack_version: int
    version: str

    @classmethod
    @override
    def from_file(cls, path: Path) -> 'PatchConfig':
        """Override to return defaults if file doesn't exist."""
        if path.exists():
            return super().from_file(path)
        else:
            return cls(pack_version=1, version="0.0.4")

    @classmethod
    def from_package_dir(cls, package_dir: Path) -> 'PatchConfig':
        """Load config from package directory, returning defaults if missing."""
        config_path = package_dir / 'config.json'
        return cls.from_file(config_path)
