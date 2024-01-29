from typing import Any
from unittest.mock import Mock

from dfu.api import DfuPlugin, Event, Store


def test_plugin():
    class TestPlugin(DfuPlugin):
        def handle(self, event: Event, **kwargs) -> Any:
            pass

    def entrypoint(store: Store) -> DfuPlugin:
        return TestPlugin()

    plugin = entrypoint(Mock())
    assert isinstance(plugin, TestPlugin)
