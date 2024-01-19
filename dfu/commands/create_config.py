import os
import subprocess
from pathlib import Path
from tempfile import NamedTemporaryFile

import click
import msgspec
from tomlkit import dumps

from dfu.config import Btrfs, Config
from dfu.snapshots.btrfs import get_all_subvolumes
from dfu.snapshots.snapper import Snapper
from dfu.snapshots.sort_snapper_configs import sort_snapper_configs


def create_config(file: Path, snapper_configs: tuple[str, ...]):
    all_subvolumes = set(get_all_subvolumes())
    all_snapper_configs = Snapper.get_configs()
    unknown_configs = set(snapper_configs) - set([c.name for c in all_snapper_configs])
    if unknown_configs:
        click.echo(f"The following snapper configs were not found: {unknown_configs}", err=True)
        raise ValueError("Unknown snapper configs")

    snapper_configs = sort_snapper_configs([c for c in all_snapper_configs if c.name in snapper_configs])

    snapper_subvolumes = set([str(Snapper(c).get_mountpoint()) for c in snapper_configs])
    missing_subvolumes = all_subvolumes - snapper_subvolumes
    if missing_subvolumes:
        click.echo(f"A snapper config was not found for the following subvolumes: {missing_subvolumes}", err=True)

    config = Config(btrfs=Btrfs(snapper_configs=snapper_configs))
    toml: bytes = msgspec.toml.encode(config)
    try:
        file.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
        with open(file, "wb") as f:
            f.write(toml)
            f.flush()
            os.chmod(file, 0o644)
    except PermissionError:
        subprocess.run(["sudo", "mkdir", "-p", str(file.parent.resolve())], check=True)
        with NamedTemporaryFile(mode="wb+") as f:
            f.write(toml)
            f.flush()
            subprocess.run(["sudo", "cp", f.name, str(file.resolve())], check=True)
        subprocess.run(["sudo", "chown", "root:root", file.resolve()], check=True)
        subprocess.run(["sudo", "chmod", "644", file.resolve()], check=True)
