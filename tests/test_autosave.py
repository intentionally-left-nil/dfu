from pathlib import Path

import pytest

from dfu.api import Event, State, Store
from dfu.config import Config
from dfu.package.dfu_diff import DfuDiff
from dfu.package.install import Install
from dfu.package.package_config import PackageConfig
from dfu.package.uninstall import Uninstall
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


def test_update_dfu_diff(store: Store):
    diff = DfuDiff(from_index=0, to_index=42)
    store.state = store.state.update(diff=diff)
    assert DfuDiff.from_file(store.state.package_dir / '.dfu' / 'diff.json') == diff


def test_delete_dfu_diff(store: Store):
    diff = DfuDiff(from_index=0, to_index=42)
    store.state = store.state.update(diff=diff)
    assert (store.state.package_dir / '.dfu' / 'diff.json').exists()
    store.state = store.state.update(diff=None)
    assert not (store.state.package_dir / '.dfu' / 'diff.json').exists()


def test_update_install(store: Store):
    install = Install(installed_dependencies=True)
    store.state = store.state.update(install=install)
    assert Install.from_file(store.state.package_dir / '.dfu' / 'install.json') == install


def test_delete_install(store: Store):
    install = Install(installed_dependencies=True)
    store.state = store.state.update(install=install)
    assert (store.state.package_dir / '.dfu' / 'install.json').exists()
    store.state = store.state.update(install=None)
    assert not (store.state.package_dir / '.dfu' / 'install.json').exists()


def test_update_uninstall(store: Store):
    uninstall = Uninstall(removed_dependencies=True)
    store.state = store.state.update(uninstall=uninstall)
    assert Uninstall.from_file(store.state.package_dir / '.dfu' / 'uninstall.json') == uninstall


def test_delete_uninstall(store: Store):
    uninstall = Uninstall(removed_dependencies=True)
    store.state = store.state.update(uninstall=uninstall)
    assert (store.state.package_dir / '.dfu' / 'uninstall.json').exists()
    store.state = store.state.update(uninstall=None)
    assert not (store.state.package_dir / '.dfu' / 'uninstall.json').exists()


def test_handle_no_ops(store: Store):
    # Just make sure no exception is raised
    store.dispatch(Event.INSTALL_DEPENDENCIES)
