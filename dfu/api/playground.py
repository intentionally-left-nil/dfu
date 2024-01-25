import platform
import subprocess
from pathlib import Path
from shutil import copy2, rmtree
from tempfile import mkdtemp
from typing import Iterable

import click
from unidiff import PatchedFile, PatchSet
from unidiff.constants import DEV_NULL


class Playground:
    location: Path

    def __init__(self, location: Path | None = None, prefix: str = 'dfu'):
        if location is None:
            location = Path(mkdtemp(prefix=prefix))

        self.location = location.resolve()

    def list_files_in_patch(
        self,
        patch: Path,
    ) -> set[Path]:
        # Given a patch file with a source of a/files/etc/my_file, return {/etc/my_file, }
        files: set[Path] = set()
        patch_files: list[PatchedFile] = PatchSet(patch.read_text(), metadata_only=True)
        for file in patch_files:
            for source in (file.source_file, file.target_file):
                source_path = Path(source or DEV_NULL)
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

    def copy_files_to_filesystem(self, dest: Path = Path('/')):
        root_dir = self.location / 'files'
        for file in root_dir.rglob('*'):
            if file.is_dir():
                continue
            relative_path = file.relative_to(root_dir)
            target = (dest / relative_path).resolve()

            mode = oct(file.stat(follow_symlinks=False).st_mode & 0o777)[2:]  # Strip out the leading 0o

            args = ["sudo", "install"]
            if target.exists():
                target_stat = target.stat(follow_symlinks=False)
                args.extend(["-o", str(target_stat.st_uid), "-g", str(target_stat.st_gid)])

            if platform.system() == "Darwin":
                # We have to create the directory first as a separate call, using the -d flag
                create_dir_args = args[:]

                create_dir_args.extend(["-m", "755", "-d", str(file.parent.resolve()), str(target.parent.resolve())])
                subprocess.run(
                    create_dir_args,
                    check=True,
                    capture_output=True,
                )
            else:
                args.append("-D")

            args.extend(["-m", mode, str(file.resolve()), str(target)])
            subprocess.run(
                args,
                check=True,
                capture_output=True,
            )
            click.echo(f"Updated {target}", err=True)

    def cleanup(self):
        rmtree(self.location, ignore_errors=True)
