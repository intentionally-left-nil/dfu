import os
import sys
from pathlib import Path
from typing import Literal

import click

from dfu.commands import (
    apply_package,
    create_config,
    create_package,
    create_snapshot,
    generate_diff,
    get_config_paths,
    launch_snapshot_shell,
    load_store,
    ls_files,
)
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
def init(name: str | None, description: str | None):
    final_name: str = click.prompt("Name", default=name or Path.cwd().name)
    final_description: str | None = click.prompt("Description", default=description or "", type=NullableString())
    path = create_package(name=final_name, description=final_description)
    print(path)


@main.command()
def snap():
    create_snapshot(load_store())


@main.command()
@click.option('--from', 'from_', type=int, default=0, help='Snapshot index to compute the before state')
@click.option('--to', type=int, default=-1, help='Snapshot index to compute the end state')
@click.option('--interactive', '-i', is_flag=True, help='Inspect and modify the changes', default=False)
def diff(from_: int, to: int, interactive: bool):
    generate_diff(load_store(), from_index=from_, to_index=to, interactive=interactive)


@main.command()
@click.option('--reverse', '-r', is_flag=True, help='Uninstall the package', default=False)
@click.option('--force', '-f', is_flag=True, help='Do not require confirmation', default=False)
@click.option('--interactive', '-i', is_flag=True, help='Inspect and modify the changes', default=False)
@click.option('--dry-run', help="Do not apply the changes to the computer", is_flag=True, default=False)
def apply(reverse: bool, force: bool, interactive: bool, dry_run: bool):
    apply_package(load_store(), reverse=reverse, confirm=not force, interactive=interactive, dry_run=dry_run)


@main.command(name="ls-files")
@click.option("-i", "--ignored", is_flag=True, help="Show only ignored files", default=False)
@click.option('--from', 'from_', type=int, default=0, help='Snapshot index to compute the before state')
@click.option('--to', type=int, default=-1, help='Snapshot index to compute the end state')
def ls_files_command(ignored: bool, from_: int, to: int):
    ls_files(load_store(), from_index=from_, to_index=to, only_ignored=ignored)


@click.group
def config():
    pass


@config.command(name="init")
@click.option("-s", "--snapper-config", multiple=True, default=[], help="Snapper configs to include")
@click.option("-f", "--file", help="File to write config to")
def config_init(snapper_config: list[str], file: str | None):
    if not snapper_config:
        default_configs = ",".join([c.name for c in Snapper.get_configs()])
        response = click.prompt(
            "Which snapper configs would you like to create snapshots for?",
            default=default_configs,
        )
        snapper_config = [c.strip() for c in response.split(",") if c.strip()]
    if file is None:
        file = str(click.prompt("Where would you like to store the dfu config?", default=get_config_paths()[0]))
    create_config(file=Path(file), snapper_configs=tuple(snapper_config))


@main.command()
@click.option('--id', 'id_', type=int, help='The snapshot id to chroot into', default=-1)
def shell(id_: int):
    launch_snapshot_shell(load_store(), id_)


main.add_command(config)

if __name__ == "__main__":
    if os.geteuid() == 0:
        click.echo("Don't run dfu as root")
        sys.exit(1)
    main()
