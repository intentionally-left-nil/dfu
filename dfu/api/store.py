from typing import Callable

from dfu.api.plugin import DfuPlugin, Event
from dfu.api.state import State

Callback = Callable[[State, State], None]


class Store:
    _state: State
    _callbacks: set[Callback]
    plugins: set[DfuPlugin]

    def __init__(self, state: State) -> None:
        self._state = state
        self._callbacks = set()
        self.plugins = set()

    def add_plugin(self, plugin: DfuPlugin) -> None:
        self.plugins.add(plugin)

    def subscribe(self, callback: Callback) -> None:
        self._callbacks.add(callback)

    def unsubscribe(self, callback: Callback) -> None:
        self._callbacks.remove(callback)

    def dispatch(self, event: Event) -> None:
        for plugin in self.plugins:
            plugin.handle(event)

    @property
    def state(self) -> State:
        return self._state

    @state.setter
    def state(self, state: State) -> None:
        old_state = self._state
        self._state = state
        for callback in self._callbacks:
            callback(old_state, state)
