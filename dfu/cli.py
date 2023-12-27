import os
import sys
from pathlib import Path

import click

from dfu.commands import (
    create_config,
    create_distribution,
    create_package,
    create_post_snapshot,
    create_pre_snapshot,
    diff_snapshot,
    get_config_paths,
    get_package_path,
    load_config,
)
from dfu.config import Config
from dfu.snapshots.snapper import Snapper


class NullableString(click.ParamType):
    name = "string"

    def convert(self, value, param, ctx):
        if value == "":
            return None
        return value


@click.group()
def main():
    pass


@main.command()
@click.option("-n", "--name", help="Name of the package")
@click.option("-d", "--description", help="Description of the package")
def new(name: str | None, description: str | None):
    final_name: str = click.prompt("Name", default=name)
    final_description: str | None = click.prompt("Description", default=description or "", type=NullableString())
    config = load_config()
    path = create_package(config, name=final_name, description=final_description)
    print(path)


@main.command()
@click.argument("package_name")
def begin(package_name: str):
    config = load_config()
    package_path = get_package_path(config, package_name)
    create_pre_snapshot(config, package_path)


@main.command()
@click.argument("package_name")
def end(package_name: str):
    config = load_config()
    package_path = get_package_path(config, package_name)
    create_post_snapshot(package_path)


@main.command()
@click.argument("package_name")
def diff(package_name: str):
    config = load_config()
    package_path = get_package_path(config, package_name)
    diff_snapshot(config, package_path)


@main.command()
@click.argument("package_name")
def dist(package_name: str):
    config = load_config()
    package_path = get_package_path(config, package_name)
    create_distribution(package_path)


@click.group
def config():
    pass


@config.command()
@click.option("-s", "--snapper-config", multiple=True, default=[], help="Snapper configs to include")
@click.option("-p", "--package-dir", help="Directory to store packages in")
@click.option("-f", "--file", help="File to write config to")
def init(snapper_config: list[str], package_dir: str | None, file: str | None):
    if not snapper_config:
        click.echo("Querying to see which snapper configs exist (sudo needed)", file=sys.stderr)
        default_configs = ",".join([c.name for c in Snapper.get_configs()])
        response = click.prompt(
            "Which snapper configs would you like to create snapshots for?",
            default=default_configs,
        )
        snapper_config = [c.strip() for c in response.split(",") if c.strip()]
    if package_dir is None:
        package_dir = click.prompt(
            "Where would you like to store the dfu packages you create?", default=Config.get_default_package_dir()
        )

    if file is None:
        file = str(click.prompt("Where would you like to store the dfu config?", default=get_config_paths()[0]))
    create_config(file=Path(file), snapper_configs=snapper_config, package_dir=package_dir)


main.add_command(config)


if __name__ == "__main__":
    if os.geteuid() == 0:
        click.echo("Don't run dfu as root")
        sys.exit(1)
    main()
