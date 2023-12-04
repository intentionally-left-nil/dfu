from subprocess import CalledProcessError
from unittest.mock import Mock, patch

import pytest

from dfu.installed_packages.pacman import get_installed_packages


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
