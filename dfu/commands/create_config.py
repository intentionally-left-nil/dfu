import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

import click
from tomlkit import dumps

from dfu.config import Btrfs, Config
from dfu.snapshots.btrfs import get_all_subvolumes
from dfu.snapshots.snapper import Snapper


def create_config(file: Path, snapper_configs: list[str], package_dir: str | None):
    all_subvolumes = set(get_all_subvolumes())
    snapper_subvolumes = set([str(Snapper(c).get_mountpoint()) for c in snapper_configs])
    missing_subvolumes = all_subvolumes - snapper_subvolumes
    if missing_subvolumes:
        click.echo(f"A snapper config was not found for the following subvolumes: {missing_subvolumes}", err=True)

    config = Config(btrfs=Btrfs(snapper_configs=snapper_configs), package_dir=package_dir)
    toml = dumps(config.__dict__)
    try:
        with open(file, "w", encoding='utf-8') as f:
            f.write(toml)
            f.flush()
    except PermissionError:
        with NamedTemporaryFile(mode="w+", encoding="utf-8") as f:
            f.write(toml)
            f.flush()

            subprocess.run(["sudo", "chown", "root:root", f.name], check=True)
            subprocess.run(["sudo", "cp", f.name, file], check=True)
        pass
