from dfu.api import DfuPlugin, State, Store
from dfu.api.plugin import Event


class AutosavePlugin(DfuPlugin):
    def __init__(self, store: Store) -> None:
        store.subscribe(self.on_change)

    def handle(self, event: Event) -> None:
        pass

    def on_change(self, old_state: State, new_state: State) -> None:
        if old_state.package_config is not new_state.package_config or old_state.package_dir != new_state.package_dir:
            new_state.package_config.write(new_state.package_dir / 'dfu_config.json')


def entrypoint(store: Store) -> AutosavePlugin:
    return AutosavePlugin(store)
