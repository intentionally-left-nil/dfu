from pathlib import Path

import click

from dfu.config import Config
from dfu.package.package_config import PackageConfig


def load_package_config(config: Config, token: str):
    package_path = get_package_path(config, token)
    return PackageConfig.from_file(package_path)


def get_package_path(config: Config, token: str) -> Path:
    package_dir = Path(config.package_dir)
    matches = list(package_dir.glob(f"{token}*/dfu_config.json"))
    if len(matches) == 0:
        raise ValueError(f"No package found matching {token}")

    if len(matches) == 1:
        return matches[0]

    click.echo("Multiple packages found:")
    for i, match in enumerate(matches, start=1):
        click.echo(f"{i}: {match}")
    choice: int = click.prompt("Please choose one", type=click.IntRange(1, len(matches)))
    return matches[choice - 1]
