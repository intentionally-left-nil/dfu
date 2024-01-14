from pathlib import Path
from unittest.mock import Mock

import pytest

from dfu.api.plugin import DfuPlugin
from dfu.api.state import State
from dfu.api.store import Callback, Store
from dfu.config import Config
from dfu.package.package_config import PackageConfig


@pytest.fixture
def state(config: Config, package_config: PackageConfig) -> State:
    return State(config=config, package_dir=Path("test"), package_config=package_config)


def test_subscribe(state: State):
    store = Store(state)
    mock_callback = Mock(spec=Callback)
    store.subscribe(mock_callback)
    assert mock_callback in store._callbacks


def test_unsubscribe(state: State):
    store = Store(state)
    mock_callback = Mock(spec=Callback)
    store.subscribe(mock_callback)
    store.unsubscribe(mock_callback)
    assert mock_callback not in store._callbacks


def test_unsubscribe_not_subscribed(state: State):
    store = Store(state)
    mock_callback = Mock(spec=Callback)
    with pytest.raises(KeyError):
        store.unsubscribe(mock_callback)


def test_state_setter(state: State, package_config: PackageConfig):
    store = Store(state)
    mock_callback = Mock(spec=Callback)
    store.subscribe(mock_callback)
    old_state = store.state
    new_state = store.state.update(package_config=package_config)
    store.state = new_state
    mock_callback.assert_called_once_with(old_state, new_state)


def test_state_setter_no_callbacks(state: State):
    store = Store(state)
    new_state = state.update(package_dir=Path("test2"))
    store.state = new_state
    assert store.state == new_state


def test_state_setter_multiple_callbacks(state: State):
    store = Store(state)
    mock_callback1 = Mock(spec=Callback)
    mock_callback2 = Mock(spec=Callback)
    store.subscribe(mock_callback1)
    store.subscribe(mock_callback2)
    old_state = store.state
    new_state = store.state.update(package_dir=Path("test2"))
    store.state = new_state
    mock_callback1.assert_called_once_with(old_state, new_state)
    mock_callback2.assert_called_once_with(old_state, new_state)


def test_add_plugin(state: State):
    store = Store(state)
    mock_plugin = Mock(spec=DfuPlugin)
    store.add_plugin(mock_plugin)
    assert mock_plugin in store.plugins
