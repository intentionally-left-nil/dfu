import os
import pwd
import subprocess
from contextlib import contextmanager
from pathlib import Path
from shutil import rmtree
from tempfile import mkdtemp
from typing import Generator

import click
from unidiff import PatchedFile, PatchSet
from unidiff.constants import DEV_NULL

from dfu.package.patch_config import PatchConfig
from dfu.revision.git import git_add_remote, git_apply, git_fetch


class Playground:
    location: Path

    def __init__(self, location: Path | None = None, prefix: str = 'dfu') -> None:
        if location is None:
            location = Path(mkdtemp(prefix=prefix))

        self.location = location.resolve()

    @classmethod
    @contextmanager
    def temporary(cls, location: Path | None = None, prefix: str = 'dfu') -> Generator['Playground', None, None]:
        playground = cls(location=location, prefix=prefix)
        try:
            yield playground
        finally:
            playground.cleanup()

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

                if (len(source_path.parts) == 2 and source_path.parts[1] in ['acl.txt', 'config.json']) or (
                    len(source_path.parts) >= 3 and source_path.parts[1] == 'files'
                ):
                    files.add(Path('/', *source_path.parts[2:]))
                else:
                    raise ValueError(f"Unexpected source file path: {source_path}")

        return files

    def copy_files_from_filesystem(self, paths: list[Path] | set[Path]) -> None:
        current_user = pwd.getpwuid(os.getuid()).pw_name
        for path in paths:
            if path.is_dir():
                continue
            relative_path = path.resolve().relative_to(Path('/'))
            target = (self.location / 'files' / relative_path).resolve()
            target.parent.mkdir(mode=0o755, parents=True, exist_ok=True)
            subprocess.run(
                [
                    'sudo',
                    'install',
                    '-m',
                    '755',
                    '-o',
                    current_user,
                    '-g',
                    current_user,
                    str(path.resolve()),
                    str(target),
                ],
                capture_output=True,
                check=True,
            )

    def apply_patch(self, patch: Path, *, reverse: bool = False) -> bool:
        self._fetch_bundle(patch.with_suffix('.pack'))

        try:
            git_apply(self.location, patch, include=['config.json'])
            config = PatchConfig.from_file(self.location / 'config.json')
            if config.pack_format != 2:
                raise ValueError(
                    f"Unsupported pack version {config.pack_format} for patch {patch.name}. Only version 2 is supported."
                )
        except subprocess.CalledProcessError:
            raise ValueError(f"Patch {patch.name} does not contain config.json. Only version 2 patches are supported.")

        try:
            click.echo(f"Applying patch {patch.name}", err=True)
            merged_cleanly = git_apply(self.location, patch, reverse=reverse)
            return merged_cleanly
        except subprocess.CalledProcessError as e:
            click.echo(f"Failed to apply patch {patch.name}", err=True)
            click.echo(e.output, err=True)
            raise e

    def _fetch_bundle(self, bundle: Path) -> None:
        if bundle.exists():
            remote_name = bundle.stem
            try:
                git_add_remote(self.location, remote_name, str(bundle.resolve()))
            except subprocess.CalledProcessError as e:
                # If the remote already exists (because we were resolving a merge conflict),
                # then just ignore the error
                if e.returncode != 3:
                    raise e

            git_fetch(self.location, remote_name)
        else:
            click.echo("No bundle file found for patch {patch.name}. Continuing without it", err=True)

    def copy_files_to_filesystem(self, dest: Path = Path('/')) -> None:
        root_dir = self.location / 'files'
        if not root_dir.exists():
            return

        subprocess.run(
            ["sudo", "cp", "--recursive", "--preserve=all", str(root_dir.resolve()) + "/.", str(dest)],
            check=True,
            capture_output=True,
        )
        click.echo(f"Updated files in {dest}", err=True)

    def cleanup(self) -> None:
        rmtree(self.location, ignore_errors=True)
