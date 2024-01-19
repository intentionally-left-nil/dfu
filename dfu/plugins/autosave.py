from dfu.api import Callback, DfuPlugin, Entrypoint, State, Store
from dfu.api.plugin import Event


class AutosavePlugin(DfuPlugin):
    def __init__(self, store: Store):
        store.subscribe(self.on_change)

    def handle(self, event: Event):
        pass

    def on_change(self, old_state: State, new_state: State):
        if old_state.package_config is not new_state.package_config or old_state.package_dir != new_state.package_dir:
            new_state.package_config.write(new_state.package_dir / 'dfu_config.json')

        if new_state.diff and (old_state.diff is not new_state.diff or old_state.package_dir != new_state.package_dir):
            (new_state.package_dir / '.dfu').mkdir(mode=0o755, exist_ok=True)
            new_state.diff.write(new_state.package_dir / '.dfu' / 'diff.json')


entrypoint: Entrypoint = lambda store: AutosavePlugin(store)
