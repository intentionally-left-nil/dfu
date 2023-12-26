import os
import sys

import click

from dfu.commands.create_distribution import create_distribution
from dfu.commands.create_package import create_package
from dfu.commands.create_snapshot import create_post_snapshot, create_pre_snapshot
from dfu.commands.diff import diff_snapshot
from dfu.commands.load_config import load_config
from dfu.commands.load_package_config import get_package_path


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


if __name__ == "__main__":
    if os.geteuid() == 0:
        click.echo("Don't run dfu as root")
        sys.exit(1)
    main()
