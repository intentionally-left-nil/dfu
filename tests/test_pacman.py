from pathlib import Path
from subprocess import CalledProcessError
from unittest.mock import MagicMock, Mock, patch

import pytest

from dfu.config import Config
from dfu.installed_packages.pacman import Diff, diff_packages, get_installed_packages
from dfu.snapshots.snapper import Snapper


@patch('subprocess.run')
def test_get_installed_packages_success(mock_run, config: Config):
    mock_run.return_value = Mock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = '''
package1
package3
package2
      
    leading_whitespace
    leading_and_trailing_whitespace    
'''
    result = get_installed_packages(config)
    assert result == ['leading_and_trailing_whitespace', 'leading_whitespace', 'package1', 'package2', 'package3']


@patch('subprocess.run')
def test_get_installed_packages_from_proot(mock_run: MagicMock, config: Config):
    mock_run.return_value = Mock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = '''
package1
package3
package2
'''
    with patch.object(Snapper, 'get_mountpoint', new=lambda self: Path(f"/{self.snapper_name}")):
        result = get_installed_packages(config, snapshot_mapping={'root': 1, 'home': 2, 'log': 3})
    assert result == ['package1', 'package2', 'package3']
    mock_run.assert_called_once_with(
        [
            'proot',
            '-r',
            '/root/.snapshots/1/snapshot',
            '-b',
            '/home/.snapshots/2/snapshot:/home',
            '-b',
            '/log/.snapshots/3/snapshot:/log',
            '-b',
            '/dev',
            '-b',
            '/proc',
            'pacman',
            '-Qqe',
        ],
        capture_output=True,
        text=True,
        check=True,
    )


@patch('subprocess.run')
def test_get_installed_packages_failure(mock_run, config: Config):
    mock_run.side_effect = CalledProcessError(1, 'cmd')

    with pytest.raises(CalledProcessError):
        get_installed_packages(config)


class TestDiffPackages:
    def test_no_changes(self):
        old_packages = ['package1', 'package2', 'package3']
        new_packages = ['package1', 'package2', 'package3']
        assert diff_packages(old_packages, new_packages) == Diff(set(), set())

    def test_added_packages(self):
        old_packages = ['package1', 'package2']
        new_packages = ['package1', 'package2', 'package3']
        assert diff_packages(old_packages, new_packages) == Diff({'package3'}, set())

    def test_removed_packages(self):
        old_packages = ['package1', 'package2', 'package3']
        new_packages = ['package1', 'package2']
        assert diff_packages(old_packages, new_packages) == Diff(set(), {'package3'})

    def test_added_and_removed_packages(self):
        old_packages = ['package1', 'package2']
        new_packages = ['package2', 'package3']
        assert diff_packages(old_packages, new_packages) == Diff({'package3'}, {'package1'})

    def test_diff_packages_with_duplicates(self):
        old_packages = ['package1', 'package2', 'package2']
        new_packages = ['package1', 'package2', 'package2', 'package3']
        assert diff_packages(old_packages, new_packages) == Diff({'package3'}, set())
