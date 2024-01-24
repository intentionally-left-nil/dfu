import subprocess
from pathlib import Path
from shutil import copy2, rmtree
from tempfile import mkdtemp
from typing import Iterable

from unidiff import PatchedFile, PatchSet
from unidiff.constants import DEV_NULL


class Playground:
    location: Path

    def __init__(self, prefix: str = 'dfu'):
        self.location = Path(mkdtemp(prefix=prefix)).resolve()

    def list_files_in_patch(
        self,
        patch: Path,
    ) -> set[Path]:
        # Given a patch file with a source of a/files/etc/my_file, return {/etc/my_file, }
        files: set[Path] = set()
        patch_files: list[PatchedFile] = PatchSet(patch.read_text(), metadata_only=True)
        for file in patch_files:
            for source in (file.source_file, file.target_file):
                source_path = Path(source)
                if source_path == Path(DEV_NULL) or source_path.parts[1:] == Path(DEV_NULL).parts[1:]:
                    continue

                if len(source_path.parts) < 3 or source_path.parts[1] != "files":
                    raise ValueError(f"Unexpected source file path: {source_path}")

                files.add(Path('/', *source_path.parts[2:]))
        return files

    def copy_files_from_filesystem(self, paths: Iterable[Path]):
        for path in paths:
            if path.is_dir():
                continue
            relative_path = path.resolve().relative_to(Path('/'))
            target = (self.location / 'files' / relative_path).resolve()
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                copy2(path, target, follow_symlinks=False)
            except PermissionError:
                subprocess.run(
                    ["sudo", "cp", "-p", "-P", path.resolve(), target.resolve()],
                    check=True,
                    capture_output=True,
                )

    def cleanup(self):
        rmtree(self.location, ignore_errors=True)
