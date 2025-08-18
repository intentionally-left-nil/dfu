import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AclEntry:
    path: Path
    mode: str
    uid: str
    gid: str

    def __post_init__(self) -> None:
        if not self.path.is_absolute():
            raise ValueError(f"Invalid path: {self.path} - must be an absolute path starting with /")
        if not re.match(r'^[0-7]+$', self.mode):
            raise ValueError(f"Invalid mode: {self.mode} - must be octal digits only (0-7)")

        if not re.match(r'^[a-zA-Z0-9_-]+$', self.uid):
            raise ValueError(f"Invalid uid: {self.uid} - must be alphanumeric with optional hyphens/underscores")

        if not re.match(r'^[a-zA-Z0-9_-]+$', self.gid):
            raise ValueError(f"Invalid gid: {self.gid} - must be alphanumeric with optional hyphens/underscores")


@dataclass(frozen=True)
class AclFile:
    entries: dict[Path, AclEntry]

    @classmethod
    def from_string(cls, content: str) -> "AclFile":
        entries = {}
        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                raise ValueError(f"Invalid line: {line}")
            gid = parts[-1].strip()
            uid = parts[-2].strip()
            mode = parts[-3].strip()
            path = Path(" ".join(parts[:-3]).strip())
            row = AclEntry(path, mode, uid, gid)
            entries[path] = row
        return cls(entries)

    @classmethod
    def from_file(cls, path: Path) -> "AclFile":
        with open(path, "r") as f:
            content = f.read()
        return cls.from_string(content)

    def write(self, path: Path) -> None:
        rows = [
            f"{entry.path} {entry.mode} {entry.uid} {entry.gid}\n"
            for entry in sorted(self.entries.values(), key=lambda x: x.path)
        ]
        with open(path, "w") as f:
            f.writelines(rows)
