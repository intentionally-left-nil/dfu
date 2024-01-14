from dfu.api.entrypoint import Entrypoint
from dfu.api.plugin import DfuPlugin, Event
from dfu.api.store import Store


class PacmanPlugin(DfuPlugin):
    store: Store

    def __init__(self, store: Store):
        self.store = store

    def handle(self, event: Event):
        if event == Event.TARGET_BRANCH_FINALIZED:
            print("PacmanPlugin: Target branch finalized")


entrypoint: Entrypoint = lambda store: PacmanPlugin(store)
