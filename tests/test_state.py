from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from dfu.api.state import State
from dfu.config import Config
from dfu.package.package_config import PackageConfig


def test_state_is_immutable(config: Config, package_config: PackageConfig) -> None:
    state = State(config=config, package_dir=Path("test"), package_config=package_config)
    with pytest.raises(FrozenInstanceError):
        state.package_dir = Path("test2")  # type: ignore


def test_update_state(config: Config, package_config: PackageConfig) -> None:
    state = State(config=config, package_dir=Path("test"), package_config=package_config)
    state = state.update(package_config=package_config, package_dir=Path("test2"))
    assert state == State(config=config, package_dir=Path("test2"), package_config=package_config)
