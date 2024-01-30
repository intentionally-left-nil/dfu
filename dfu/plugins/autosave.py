from dfu.api import Callback, DfuPlugin, Entrypoint, State, Store
from dfu.api.plugin import Event


class AutosavePlugin(DfuPlugin):
    def __init__(self, store: Store):
        store.subscribe(self.on_change)

    def handle(self, event: Event, **kwargs):
        pass

    def on_change(self, old_state: State, new_state: State):
        if old_state.package_config is not new_state.package_config or old_state.package_dir != new_state.package_dir:
            new_state.package_config.write(new_state.package_dir / 'dfu_config.json')


entrypoint: Entrypoint = lambda store: AutosavePlugin(store)
