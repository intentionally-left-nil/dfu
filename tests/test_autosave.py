from pathlib import Path

import pytest

from dfu.api import Event, State, Store
from dfu.config import Config
from dfu.package.package_config import PackageConfig
from dfu.plugins.autosave import AutosavePlugin


@pytest.fixture
def store(tmp_path: Path, config: Config, package_config: PackageConfig) -> Store:
    package_config.write(tmp_path / 'dfu_config.json')

    store = Store(State(config=config, package_dir=tmp_path, package_config=package_config))
    store.add_plugin(AutosavePlugin(store))
    return store


def test_save_package_config(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(description="Updated the description")
    )
    assert PackageConfig.from_file(store.state.package_dir / 'dfu_config.json') == store.state.package_config


def test_handle_no_ops(store: Store):
    # Just make sure no exception is raised
    store.dispatch(Event.INSTALL_DEPENDENCIES)
