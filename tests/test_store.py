from unittest.mock import Mock

import pytest

from dfu.api.state import State
from dfu.api.store import Callback, Store
from dfu.package.package_config import PackageConfig


def test_subscribe():
    store = Store()
    mock_callback = Mock(spec=Callback)
    store.subscribe(mock_callback)
    assert mock_callback in store._callbacks


def test_unsubscribe():
    store = Store()
    mock_callback = Mock(spec=Callback)
    store.subscribe(mock_callback)
    store.unsubscribe(mock_callback)
    assert mock_callback not in store._callbacks


def test_unsubscribe_not_subscribed():
    store = Store()
    mock_callback = Mock(spec=Callback)
    with pytest.raises(KeyError):
        store.unsubscribe(mock_callback)


def test_state_setter(package_config: PackageConfig):
    store = Store()
    mock_callback = Mock(spec=Callback)
    store.subscribe(mock_callback)
    old_state = store.state
    new_state = State(package_config=package_config)
    store.state = new_state
    mock_callback.assert_called_once_with(old_state, new_state)


def test_state_setter_no_callbacks():
    store = Store()
    new_state = State()
    store.state = new_state
    assert store.state == new_state


def test_state_setter_multiple_callbacks():
    store = Store()
    mock_callback1 = Mock(spec=Callback)
    mock_callback2 = Mock(spec=Callback)
    store.subscribe(mock_callback1)
    store.subscribe(mock_callback2)
    old_state = store.state
    new_state = State()
    store.state = new_state
    mock_callback1.assert_called_once_with(old_state, new_state)
    mock_callback2.assert_called_once_with(old_state, new_state)
