from contextlib import contextmanager
from pathlib import Path
from types import MappingProxyType
from typing import Generator, TypedDict
from unittest.mock import Mock, patch

import pytest

from dfu.api import Event, State, Store
from dfu.config import Config
from dfu.package.dfu_diff import DfuDiff
from dfu.package.package_config import PackageConfig
from dfu.plugins.pacman import PacmanPlugin
from dfu.snapshots.proot import proot
from dfu.snapshots.snapper import Snapper


@pytest.fixture
def store(config: Config) -> Store:
    state = State(
        config=config,
        package_dir=Path("test"),
        package_config=PackageConfig(
            name="test",
            description="my cool description",
            programs_added=tuple(),
            snapshots=(MappingProxyType({"root": 1, "home": 1}), MappingProxyType({"root": 2, "home": 2})),
            version="0.0.2",
        ),
        diff=DfuDiff(
            from_index=0,
            to_index=1,
            copied_pre_files=True,
            copied_post_files=True,
            updated_installed_programs=False,
        ),
    )
    store = Store(state)
    plugin = PacmanPlugin(store)
    store.add_plugin(plugin)
    return store


@pytest.fixture(autouse=True)
def mock_get_mountpoint():
    with patch.object(Snapper, 'get_mountpoint', new=lambda self: Path(f"/{self.snapper_name}")):
        yield


@contextmanager
def mock_subprocess_run(installed_packages: set[str] | None = None) -> Generator[Mock, None, None]:
    def side_effect(*args, **kwargs):
        if args[0][:-1] == ['pacman', '-Q']:
            if args[0][-1] in installed_packages:
                return Mock(returncode=0)
            else:
                return Mock(returncode=1)

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = side_effect
        yield mock_run


@contextmanager
def mock_proot(store: Store, before: str, after: str) -> Generator[None, None, None]:
    before_args = proot(['pacman', '-Qqe'], config=store.state.config, snapshot=store.state.package_config.snapshots[0])
    after_args = proot(['pacman', '-Qqe'], config=store.state.config, snapshot=store.state.package_config.snapshots[1])

    installed_packages = set()

    def side_effect(*args, **kwargs):
        if args[0] == before_args:
            return Mock(returncode=0, stdout=before)
        elif args[0] == after_args:
            return Mock(returncode=0, stdout=after)
        else:
            raise ValueError(f"Unexpected args: {args}")

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = side_effect
        yield


def test_one_package_added(store: Store):
    before = 'package1\npackage2\npackage3\n'
    after = 'package1\nnew_package\npackage2\npackage3\n'
    with mock_proot(store, before, after):
        store.dispatch(Event.TARGET_BRANCH_FINALIZED)
    assert store.state.package_config.programs_added == ('new_package',)


def test_trims_whitespace(store: Store):
    after = '''
package1
package3
package2
      
    leading_whitespace
    leading_and_trailing_whitespace    
'''
    with mock_proot(store, '', after):
        store.dispatch(Event.TARGET_BRANCH_FINALIZED)
    assert store.state.package_config.programs_added == (
        'leading_and_trailing_whitespace',
        'leading_whitespace',
        'package1',
        'package2',
        'package3',
    )


def test_no_packages_added(store: Store):
    before = 'package1\npackage2\npackage3\n'
    after = 'package1\npackage2\npackage3\n'
    with mock_proot(store, before, after):
        store.dispatch(Event.TARGET_BRANCH_FINALIZED)
    assert store.state.package_config.programs_added == tuple()


def test_packages_added_and_removed(store: Store):
    before = 'package1\npackage2\npackage3\n'
    after = 'package1\npackage3\npackage4\n'
    with mock_proot(store, before, after):
        store.dispatch(Event.TARGET_BRANCH_FINALIZED)
    assert store.state.package_config.programs_added == ('package4',)
    assert store.state.package_config.programs_removed == ('package2',)


def test_appends_to_existing_updates(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'other_new_package'), programs_removed=('package_removed',)
        )
    )
    before = 'package1\npackage2\npackage3\n'
    after = 'package1\nnew_package\n\npackage3\n'
    with mock_proot(store, before, after):
        store.dispatch(Event.TARGET_BRANCH_FINALIZED)
    assert store.state.package_config.programs_added == ('new_package', 'other_new_package', 'package1')
    assert store.state.package_config.programs_removed == ('package2', 'package_removed')


def test_install_zero_dependencies(store: Store):
    with patch('subprocess.run') as mock_run:
        store.dispatch(Event.INSTALL_DEPENDENCIES)
        mock_run.assert_not_called()


def test_install_dependencies(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    with patch('subprocess.run') as mock_run:
        store.dispatch(Event.INSTALL_DEPENDENCIES)
        mock_run.assert_called_once_with(['sudo', 'pacman', '-S', '--needed', 'package1', 'package2'], check=True)


def test_remove_and_install_a_dependency(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'package2'), programs_removed=('package3', 'package4')
        )
    )
    with mock_subprocess_run(installed_packages={'package3', 'package4'}) as mock_run:
        store.dispatch(Event.INSTALL_DEPENDENCIES)
        mock_run.assert_any_call(['sudo', 'pacman', '-S', '--needed', 'package1', 'package2'], check=True)
        mock_run.assert_any_call(['sudo', 'pacman', '-R', 'package3', 'package4'], check=True)


def test_remove_and_install_a_dependency_skips_if_one_not_installed(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'package2'), programs_removed=('package3', 'package4')
        )
    )
    with mock_subprocess_run(installed_packages={'package3', 'not_package4'}) as mock_run:
        store.dispatch(Event.INSTALL_DEPENDENCIES)
        mock_run.assert_any_call(['sudo', 'pacman', '-S', '--needed', 'package1', 'package2'], check=True)
        mock_run.assert_any_call(['sudo', 'pacman', '-R', 'package3'], check=True)


def test_remove_and_install_a_dependency_skips_if_none_installed(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'package2'), programs_removed=('package3', 'package4')
        )
    )
    with mock_subprocess_run(installed_packages={'not_package3', 'not_package4'}) as mock_run:
        store.dispatch(Event.INSTALL_DEPENDENCIES)
        assert mock_run.call_count == 3
        mock_run.assert_any_call(['sudo', 'pacman', '-S', '--needed', 'package1', 'package2'], check=True)
        mock_run.assert_any_call(['pacman', '-Q', 'package3'], capture_output=True, text=True)
        mock_run.assert_any_call(['pacman', '-Q', 'package4'], capture_output=True, text=True)


def test_uninstall_zero_dependencies(store: Store):
    with mock_subprocess_run(installed_packages={'package3', 'package4'}) as mock_run:
        store.dispatch(Event.UNINSTALL_DEPENDENCIES)
        mock_run.assert_not_called()


def test_uninstall_dependencies(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    with mock_subprocess_run(installed_packages={'package1', 'package2'}) as mock_run:
        store.dispatch(Event.UNINSTALL_DEPENDENCIES)
        mock_run.assert_any_call(['sudo', 'pacman', '-R', 'package1', 'package2'], check=True)


def test_uninstall_dependencies_skips_one_not_installed(store: Store):
    store.state = store.state.update(package_config=store.state.package_config.update(programs_added=('package1',)))
    with mock_subprocess_run(installed_packages={'package1', 'package2'}) as mock_run:
        store.dispatch(Event.UNINSTALL_DEPENDENCIES)
        mock_run.assert_any_call(['sudo', 'pacman', '-R', 'package1'], check=True)


def test_uninstall_dependencies_skips_if_none_are_installed(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    with mock_subprocess_run(installed_packages={'some_other_package', 'another_different_package'}) as mock_run:
        store.dispatch(Event.UNINSTALL_DEPENDENCIES)
        assert mock_run.call_count == 2
        mock_run.assert_any_call(['pacman', '-Q', 'package1'], capture_output=True, text=True)
        mock_run.assert_any_call(['pacman', '-Q', 'package2'], capture_output=True, text=True)


def test_uninstall_and_readd_a_dependency(store: Store):
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'package2'), programs_removed=('package3', 'package4')
        )
    )
    with mock_subprocess_run(installed_packages={'package1', 'package2'}) as mock_run:
        store.dispatch(Event.UNINSTALL_DEPENDENCIES)
        mock_run.assert_any_call(['sudo', 'pacman', '-R', 'package1', 'package2'], check=True)
        mock_run.assert_any_call(['sudo', 'pacman', '-S', '--needed', 'package3', 'package4'], check=True)
