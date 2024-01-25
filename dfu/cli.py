import os
import sys
from pathlib import Path
from typing import Literal

import click

from dfu.commands import (
    abort_diff,
    abort_install,
    abort_uninstall,
    begin_diff,
    begin_install,
    begin_uninstall,
    continue_diff,
    continue_install,
    continue_uninstall,
    create_config,
    create_package,
    create_snapshot,
    get_config_paths,
    launch_shell,
    launch_snapshot_shell,
    load_store,
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
@click.option('--abort', is_flag=True, help='Abort the operation', default=None)
@click.option('--continue', 'continue_', is_flag=True, help='Continue the rebase operation', default=None)
@click.option('--from', 'from_', type=int, default=0, help='Snapshot index to compute the before state')
@click.option('--to', type=int, default=-1, help='Snapshot index to compute the end state')
def diff(abort: bool | None, continue_: bool | None, from_: int, to: int):
    if abort and continue_:
        raise ValueError("Cannot specify both --abort and --continue")
    store = load_store()
    if abort:
        abort_diff(store)
    elif continue_:
        continue_diff(store)
    else:
        begin_diff(store, from_index=from_, to_index=to)


@main.command()
@click.option('--abort', is_flag=True, help='Abort the operation', default=None)
@click.option('--continue', 'continue_', is_flag=True, help='Continue the install operation', default=None)
def install(abort: bool | None, continue_: bool | None):
    if abort and continue_:
        raise ValueError("Cannot specify both --abort and --continue")
    store = load_store()
    if abort:
        abort_install(store)
    elif continue_:
        continue_install(store)
    else:
        begin_install(store)


@main.command()
@click.option('--abort', is_flag=True, help='Abort the operation', default=None)
@click.option('--continue', 'continue_', is_flag=True, help='Continue the uninstall operation', default=None)
def uninstall(abort: bool | None, continue_: bool | None):
    if abort and continue_:
        raise ValueError("Cannot specify both --abort and --continue")
    store = load_store()
    if abort:
        abort_uninstall(store)
    elif continue_:
        continue_uninstall(store)
    else:
        begin_uninstall(store)


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
@click.option('--location', type=click.Choice(['placeholder', 'diff_files', 'install_files', 'uninstall_files']))
def shell(location: Literal['placeholder', 'diff_files', 'install_files', 'uninstall_files'] | None):
    launch_shell(load_store(), location)


@main.command()
@click.option('--id', 'id_', type=int, help='The snapshot id to chroot into', default=-1)
def snapshot_shell(id_: int):
    launch_snapshot_shell(load_store(), id_)


main.add_command(config)

if __name__ == "__main__":
    if os.geteuid() == 0:
        click.echo("Don't run dfu as root")
        sys.exit(1)
    main()
