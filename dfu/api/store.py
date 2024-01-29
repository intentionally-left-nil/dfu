from typing import Callable

from dfu.api.plugin import DfuPlugin, Event
from dfu.api.state import State

Callback = Callable[[State, State], None]


class Store:
    _state: State
    _callbacks: set[Callback]
    plugins: set[DfuPlugin]

    def __init__(self, state: State):
        self._state = state
        self._callbacks = set()
        self.plugins = set()

    def add_plugin(self, plugin: DfuPlugin):
        self.plugins.add(plugin)

    def subscribe(self, callback: Callback):
        self._callbacks.add(callback)

    def unsubscribe(self, callback: Callback):
        self._callbacks.remove(callback)

    def dispatch(self, event: Event, **kwargs):
        for plugin in self.plugins:
            plugin.handle(event, **kwargs)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state: State):
        old_state = self._state
        self._state = state
        for callback in self._callbacks:
            callback(old_state, state)
