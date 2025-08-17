from contextlib import contextmanager
from itertools import product
from pathlib import Path
from types import MappingProxyType
from typing import Any, Generator
from unittest.mock import Mock, patch

import pytest

from dfu.api import State, Store
from dfu.api.plugin import (
    InstallDependenciesEvent,
    UninstallDependenciesEvent,
    UpdateInstalledDependenciesEvent,
)
from dfu.config import Config
from dfu.package.package_config import PackageConfig
from dfu.plugins.pacman import PacmanPlugin
from dfu.snapshots.proot import proot
from dfu.snapshots.snapper import Snapper, SnapperName


@pytest.fixture
def store(config: Config) -> Store:
    state = State(
        config=config,
        package_dir=Path("test"),
        package_config=PackageConfig(
            name="test",
            description="my cool description",
            programs_added=tuple(),
            snapshots=(
                MappingProxyType({SnapperName("root"): 1, SnapperName("home"): 1}),
                MappingProxyType({SnapperName("root"): 2, SnapperName("home"): 2}),
            ),
            version="0.0.2",
        ),
    )
    store = Store(state)
    plugin = PacmanPlugin(store)
    store.add_plugin(plugin)
    return store


@pytest.fixture(autouse=True)
def mock_get_mountpoint() -> Generator[None, None, None]:
    with patch.object(Snapper, 'get_mountpoint', new=lambda self: Path(f"/{self.snapper_name}")):
        yield


@contextmanager
def mock_subprocess_run(installed_packages: set[str] | None = None) -> Generator[Mock, None, None]:
    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        if args[0][:-1] == ['pacman', '-Q']:
            if installed_packages is not None and args[0][-1] in installed_packages:
                return Mock(returncode=0)
            else:
                return Mock(returncode=1)
        return Mock()  # Default case

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = side_effect
        yield mock_run


@contextmanager
def mock_proot(store: Store, before: str, after: str) -> Generator[None, None, None]:
    before_args = proot(['pacman', '-Qqe'], config=store.state.config, snapshot=store.state.package_config.snapshots[0])
    after_args = proot(['pacman', '-Qqe'], config=store.state.config, snapshot=store.state.package_config.snapshots[1])

    def side_effect(*args: Any, **kwargs: Any) -> Mock:
        if args[0] == before_args:
            return Mock(returncode=0, stdout=before)
        elif args[0] == after_args:
            return Mock(returncode=0, stdout=after)
        else:
            raise ValueError(f"Unexpected args: {args}")

    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = side_effect
        yield


def test_one_package_added(store: Store) -> None:
    before = 'package1\npackage2\npackage3\n'
    after = 'package1\nnew_package\npackage2\npackage3\n'
    with mock_proot(store, before, after):
        store.dispatch(UpdateInstalledDependenciesEvent(from_index=0, to_index=1))
    assert store.state.package_config.programs_added == ('new_package',)


def test_trims_whitespace(store: Store) -> None:
    after = '''
package1
package3
package2
      
    leading_whitespace
    leading_and_trailing_whitespace    
'''
    with mock_proot(store, '', after):
        store.dispatch(UpdateInstalledDependenciesEvent(from_index=0, to_index=1))
    assert store.state.package_config.programs_added == (
        'leading_and_trailing_whitespace',
        'leading_whitespace',
        'package1',
        'package2',
        'package3',
    )


def test_no_packages_added(store: Store) -> None:
    before = 'package1\npackage2\npackage3\n'
    after = 'package1\npackage2\npackage3\n'
    with mock_proot(store, before, after):
        store.dispatch(UpdateInstalledDependenciesEvent(from_index=0, to_index=1))
    assert store.state.package_config.programs_added == tuple()


def test_packages_added_and_removed(store: Store) -> None:
    before = 'package1\npackage2\npackage3\n'
    after = 'package1\npackage3\npackage4\n'
    with mock_proot(store, before, after):
        store.dispatch(UpdateInstalledDependenciesEvent(from_index=0, to_index=1))
    assert store.state.package_config.programs_added == ('package4',)
    assert store.state.package_config.programs_removed == ('package2',)


def test_appends_to_existing_updates(store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'other_new_package'), programs_removed=('package_removed',)
        )
    )
    before = 'package1\npackage2\npackage3\n'
    after = 'package1\nnew_package\n\npackage3\n'
    with mock_proot(store, before, after):
        store.dispatch(UpdateInstalledDependenciesEvent(from_index=0, to_index=1))
    assert store.state.package_config.programs_added == ('new_package', 'other_new_package', 'package1')
    assert store.state.package_config.programs_removed == ('package2', 'package_removed')


def test_install_zero_dependencies(store: Store) -> None:
    with patch('subprocess.run') as mock_run:
        store.dispatch(InstallDependenciesEvent(confirm=False, dry_run=False))
        mock_run.assert_not_called()


def test_install_dependencies(store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    with patch('subprocess.run') as mock_run:
        store.dispatch(InstallDependenciesEvent(confirm=False, dry_run=False))
        mock_run.assert_called_once_with(
            ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'package1', 'package2'], check=True
        )


def test_remove_and_install_a_dependency(store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'package2'), programs_removed=('package3', 'package4')
        )
    )
    with mock_subprocess_run(installed_packages={'package3', 'package4'}) as mock_run:
        store.dispatch(InstallDependenciesEvent(confirm=False, dry_run=False))
        mock_run.assert_any_call(
            ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'package1', 'package2'], check=True
        )
        mock_run.assert_any_call(['sudo', 'pacman', '-R', '--noconfirm', 'package3', 'package4'], check=True)


def test_remove_and_install_a_dependency_skips_if_one_not_installed(store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'package2'), programs_removed=('package3', 'package4')
        )
    )
    with mock_subprocess_run(installed_packages={'package3', 'not_package4'}) as mock_run:
        store.dispatch(InstallDependenciesEvent(confirm=False, dry_run=False))
        mock_run.assert_any_call(
            ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'package1', 'package2'], check=True
        )
        mock_run.assert_any_call(['sudo', 'pacman', '-R', '--noconfirm', 'package3'], check=True)


def test_remove_and_install_a_dependency_skips_if_none_installed(store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'package2'), programs_removed=('package3', 'package4')
        )
    )
    with mock_subprocess_run(installed_packages={'not_package3', 'not_package4'}) as mock_run:
        store.dispatch(InstallDependenciesEvent(confirm=False, dry_run=False))
        assert mock_run.call_count == 3
        mock_run.assert_any_call(
            ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'package1', 'package2'], check=True
        )
        mock_run.assert_any_call(['pacman', '-Q', 'package3'], capture_output=True, text=True)
        mock_run.assert_any_call(['pacman', '-Q', 'package4'], capture_output=True, text=True)


@pytest.mark.parametrize(
    [
        'confirm',
        'dry_run',
    ],
    product([False, True], repeat=2),
)
@patch('subprocess.run')
@patch('click.confirm')
def test_install_flags(mock_confirm: Mock, mock_run: Mock, store: Store, confirm: bool, dry_run: bool) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    mock_confirm.return_value = True
    store.dispatch(InstallDependenciesEvent(confirm=confirm, dry_run=dry_run))
    if confirm:
        mock_confirm.assert_called_once()
    else:
        mock_confirm.assert_not_called()

    if dry_run:
        mock_run.assert_not_called()
    else:
        mock_run.assert_called_once_with(
            ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'package1', 'package2'], check=True
        )


@patch('subprocess.run')
@patch('click.confirm')
def test_install_confirm_no(mock_confirm: Mock, mock_run: Mock, store: Store) -> None:
    mock_confirm.return_value = False
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    store.dispatch(InstallDependenciesEvent(confirm=True, dry_run=False))
    mock_confirm.assert_called_once()
    mock_run.assert_not_called()


def test_uninstall_zero_dependencies(store: Store) -> None:
    with mock_subprocess_run(installed_packages={'package3', 'package4'}) as mock_run:
        store.dispatch(UninstallDependenciesEvent(confirm=False, dry_run=False))
        mock_run.assert_not_called()


def test_uninstall_dependencies(store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    with mock_subprocess_run(installed_packages={'package1', 'package2'}) as mock_run:
        store.dispatch(UninstallDependenciesEvent(confirm=False, dry_run=False))
        mock_run.assert_any_call(['sudo', 'pacman', '-R', '--noconfirm', 'package1', 'package2'], check=True)


def test_uninstall_dependencies_skips_one_not_installed(store: Store) -> None:
    store.state = store.state.update(package_config=store.state.package_config.update(programs_added=('package1',)))
    with mock_subprocess_run(installed_packages={'package1', 'package2'}) as mock_run:
        store.dispatch(UninstallDependenciesEvent(confirm=False, dry_run=False))
        mock_run.assert_any_call(['sudo', 'pacman', '-R', '--noconfirm', 'package1'], check=True)


def test_uninstall_dependencies_skips_if_none_are_installed(store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    with mock_subprocess_run(installed_packages={'some_other_package', 'another_different_package'}) as mock_run:
        store.dispatch(UninstallDependenciesEvent(confirm=False, dry_run=False))
        assert mock_run.call_count == 2
        mock_run.assert_any_call(['pacman', '-Q', 'package1'], capture_output=True, text=True)
        mock_run.assert_any_call(['pacman', '-Q', 'package2'], capture_output=True, text=True)


def test_uninstall_and_readd_a_dependency(store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(
            programs_added=('package1', 'package2'), programs_removed=('package3', 'package4')
        )
    )
    with mock_subprocess_run(installed_packages={'package1', 'package2'}) as mock_run:
        store.dispatch(UninstallDependenciesEvent(confirm=False, dry_run=False))
        mock_run.assert_any_call(['sudo', 'pacman', '-R', '--noconfirm', 'package1', 'package2'], check=True)
        mock_run.assert_any_call(
            ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'package3', 'package4'], check=True
        )


@pytest.mark.parametrize(
    [
        'confirm',
        'dry_run',
    ],
    product([False, True], repeat=2),
)
@patch('click.confirm')
def test_uninstall_flags(mock_confirm: Mock, store: Store, confirm: bool, dry_run: bool) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    mock_confirm.return_value = True
    with mock_subprocess_run(installed_packages={'package1', 'package2'}) as mock_run:
        store.dispatch(UninstallDependenciesEvent(confirm=confirm, dry_run=dry_run))
        if confirm:
            mock_confirm.assert_called_once()
        else:
            mock_confirm.assert_not_called()
        if dry_run:
            assert mock_run.call_count == 2
            mock_run.assert_any_call(['pacman', '-Q', 'package1'], capture_output=True, text=True)
            mock_run.assert_any_call(['pacman', '-Q', 'package2'], capture_output=True, text=True)
        else:
            mock_run.assert_any_call(['sudo', 'pacman', '-R', '--noconfirm', 'package1', 'package2'], check=True)


@patch('click.confirm')
def test_uninstall_confirm_no(mock_confirm: Mock, store: Store) -> None:
    store.state = store.state.update(
        package_config=store.state.package_config.update(programs_added=('package1', 'package2'))
    )
    mock_confirm.return_value = False
    with mock_subprocess_run(installed_packages={'package1', 'package2'}) as mock_run:
        store.dispatch(UninstallDependenciesEvent(confirm=True, dry_run=False))
        mock_confirm.assert_called_once()
        assert mock_run.call_count == 2
        mock_run.assert_any_call(['pacman', '-Q', 'package1'], capture_output=True, text=True)
        mock_run.assert_any_call(['pacman', '-Q', 'package2'], capture_output=True, text=True)
