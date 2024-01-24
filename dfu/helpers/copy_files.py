import os
import subprocess
from pathlib import Path

import click


def copy_dry_run_files(dry_run_dir: Path):
    src = dry_run_dir / "files"
    for file in src.glob('**/*'):
        if file.is_file():
            target = Path('/') / file.relative_to(src)
            if target.exists():
                stat = os.stat(src)
                subprocess.run(
                    ["sudo", "chown", f"{stat.st_uid}:{stat.st_gid}", src.resolve()], check=True, capture_output=True
                )
            try:
                subprocess.run(["cp", "-P", "-p", file.resolve(), target.resolve()], check=True, capture_output=True)
                click.echo(f"Updated  {target}", err=True)
            except PermissionError:
                subprocess.run(
                    ["sudo", "cp", "-P", "-p", file.resolve(), target.resolve()], check=True, capture_output=True
                )
                click.echo(f"Updated  {target}", err=True)
