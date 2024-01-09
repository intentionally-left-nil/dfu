from typing import Callable

from dfu.api.state import State

Callback = Callable[[State, State], None]


class Store:
    _state: State
    _callbacks: set[Callback]

    def __init__(self):
        self._state = State()
        self._callbacks = set()

    def subscribe(self, callback: Callback):
        self._callbacks.add(callback)

    def unsubscribe(self, callback: Callback):
        self._callbacks.remove(callback)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state: State):
        old_state = self._state
        self._state = state
        for callback in self._callbacks:
            callback(old_state, state)
