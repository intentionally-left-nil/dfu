from subprocess import CalledProcessError
from unittest.mock import Mock, patch

import pytest

from dfu.installed_packages.pacman import Diff, diff_packages, get_installed_packages


@patch('subprocess.run')
def test_get_installed_packages_success(mock_run):
    mock_run.return_value = Mock()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = '''
package1
package3
package2
      
    leading_whitespace
    leading_and_trailing_whitespace    
'''
    result = get_installed_packages()
    assert result == ['leading_and_trailing_whitespace', 'leading_whitespace', 'package1', 'package2', 'package3']


@patch('subprocess.run')
def test_get_installed_packages_failure(mock_run):
    mock_run.side_effect = CalledProcessError(1, 'cmd')

    with pytest.raises(CalledProcessError):
        get_installed_packages()


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
