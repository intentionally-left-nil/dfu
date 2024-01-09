from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from dfu.api.state import State
from dfu.package.package_config import PackageConfig


def test_state_is_immutable(package_config: PackageConfig):
    state = State(package_config=package_config)
    with pytest.raises(FrozenInstanceError):
        state.package_dir = Path("test")


def test_update_state(package_config: PackageConfig):
    state = State()
    state = state.update(package_config=package_config, package_dir=Path("test"))
    assert state == State(package_config=package_config, package_dir=Path("test"))
    state = state.update(package_dir=None)
    assert state == State(package_config=package_config)
