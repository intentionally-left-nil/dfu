from typing import Any
from unittest.mock import Mock

from dfu.api import DfuPlugin, Event, Store
from dfu.api.entrypoint import Entrypoint


def test_plugin():
    class TestPlugin(DfuPlugin):
        def handle(self, event: Event) -> Any:
            pass

    def _entrypoint(store: Store) -> DfuPlugin:
        return TestPlugin()

    entrypoint: Entrypoint = _entrypoint
    plugin = entrypoint(Mock())
    assert isinstance(plugin, TestPlugin)
