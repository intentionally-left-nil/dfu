import subprocess

from dfu.api.entrypoint import Entrypoint
from dfu.api.plugin import DfuPlugin, Event
from dfu.api.store import Store

# TODO: Refactor this into an API, for non btrfs/snapper roots. Then move it to the API directory
from dfu.snapshots.proot import proot


class PacmanPlugin(DfuPlugin):
    store: Store

    def __init__(self, store: Store):
        self.store = store

    def handle(self, event: Event):
        if event == Event.TARGET_BRANCH_FINALIZED:
            self.update_installed_packages()

    def update_installed_packages(self):
        assert self.store.state.diff
        old = self.get_installed_packages(self.store.state.diff.from_index)
        new = self.get_installed_packages(self.store.state.diff.to_index)

        added = list((new - old) | set(self.store.state.package_config.programs_added))
        removed = list((old - new) | set(self.store.state.package_config.programs_removed))
        added.sort()
        removed.sort()

        self.store.state = self.store.state.update(
            package_config=self.store.state.package_config.update(
                programs_added=tuple(added),
                programs_removed=tuple(removed),
            ),
            diff=self.store.state.diff.update(updated_installed_programs=True),
        )

    def get_installed_packages(self, snapshot_index: int) -> set[str]:
        args = ['pacman', '-Qqe']
        snapshot = self.store.state.package_config.snapshots[snapshot_index]
        args = proot(args, config=self.store.state.config, snapshot=snapshot)

        result = subprocess.run(args, capture_output=True, text=True, check=True)
        packages = result.stdout.split('\n')
        packages = [package.strip() for package in packages]
        return set([package for package in packages if package])


entrypoint: Entrypoint = lambda store: PacmanPlugin(store)
