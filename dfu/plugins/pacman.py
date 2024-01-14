from dfu.api.entrypoint import Entrypoint
from dfu.api.plugin import DfuPlugin


class PacmanPlugin(DfuPlugin):
    def handle(self):
        pass


entrypoint: Entrypoint = lambda store: PacmanPlugin()
