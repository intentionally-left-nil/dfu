from unittest.mock import Mock

from dfu.api.entrypoint import Entrypoint
from dfu.api.plugin import DfuPlugin


def test_plugin():
    class TestPlugin(DfuPlugin):
        def handle(self):
            pass

    entrypoint: Entrypoint = lambda store: TestPlugin()
    plugin = entrypoint(Mock())
    assert isinstance(plugin, TestPlugin)
