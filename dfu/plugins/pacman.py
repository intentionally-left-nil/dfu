import subprocess

import click

from dfu.api.entrypoint import Entrypoint
from dfu.api.plugin import DfuPlugin, Event
from dfu.api.store import Store

# TODO: Refactor this into an API, for non btrfs/snapper roots. Then move it to the API directory
from dfu.snapshots.proot import proot


class PacmanPlugin(DfuPlugin):
    store: Store

    def __init__(self, store: Store):
        self.store = store

    def handle(self, event: Event, **kwargs):
        match event:
            case Event.UPDATE_INSTALLED_DEPENDENCIES:
                self._update_installed_packages(kwargs['from_index'], kwargs['to_index'])
            case Event.INSTALL_DEPENDENCIES:
                self._install_dependencies(confirm=kwargs['confirm'], dry_run=kwargs['dry_run'])
            case Event.UNINSTALL_DEPENDENCIES:
                self._uninstall_dependencies(confirm=kwargs['confirm'], dry_run=kwargs['dry_run'])

    def _update_installed_packages(self, from_index: int, to_index: int):
        old = self._get_installed_packages(from_index)
        new = self._get_installed_packages(to_index)

        added = list((new - old) | set(self.store.state.package_config.programs_added))
        removed = list((old - new) | set(self.store.state.package_config.programs_removed))
        added.sort()
        removed.sort()

        self.store.state = self.store.state.update(
            package_config=self.store.state.package_config.update(
                programs_added=tuple(added),
                programs_removed=tuple(removed),
            ),
        )

    def _get_installed_packages(self, snapshot_index: int) -> set[str]:
        args = ['pacman', '-Qqe']
        snapshot = self.store.state.package_config.snapshots[snapshot_index]
        args = proot(args, config=self.store.state.config, snapshot=snapshot)

        result = subprocess.run(args, capture_output=True, text=True, check=True)
        packages = result.stdout.split('\n')
        packages = [package.strip() for package in packages]
        return set([package for package in packages if package])

    def _install_dependencies(self, *, confirm: bool, dry_run: bool):
        to_remove = [p for p in self.store.state.package_config.programs_removed if _is_package_installed(p)]
        _uninstall(to_remove, confirm=confirm, dry_run=dry_run)
        _install(self.store.state.package_config.programs_added, confirm=confirm, dry_run=dry_run)

    def _uninstall_dependencies(self, *, confirm: bool, dry_run: bool):
        to_remove = [p for p in self.store.state.package_config.programs_added if _is_package_installed(p)]
        _uninstall(to_remove, confirm=confirm, dry_run=dry_run)
        _install(self.store.state.package_config.programs_removed, confirm=confirm, dry_run=dry_run)


def _install(packages: list[str] | tuple[str, ...], *, confirm: bool, dry_run: bool):
    if not packages:
        return
    click.echo(f"Installing dependencies: {', '.join(packages)}", err=True)
    if not confirm or click.confirm("Would you like to continue?"):
        args = ['sudo', 'pacman', '-S', '--needed', '--noconfirm', *packages]
        if dry_run:
            click.echo("Dry run: Skipping installation", err=True)
        else:
            subprocess.run(args, check=True)


def _uninstall(packages: list[str], *, confirm: bool, dry_run: bool):
    if not packages:
        return
    click.echo(f"Removing dependencies: {', '.join(packages)}", err=True)
    if not confirm or click.confirm("Would you like to continue?"):
        args = ['sudo', 'pacman', '-R', '--noconfirm', *packages]

        if dry_run:
            click.echo("Dry run: Skipping removal", err=True)
        else:
            subprocess.run(args, check=True)


def _is_package_installed(package: str) -> bool:
    result = subprocess.run(['pacman', '-Q', package], capture_output=True, text=True)
    return result.returncode == 0


entrypoint: Entrypoint = lambda store: PacmanPlugin(store)
