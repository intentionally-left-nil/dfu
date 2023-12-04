from subprocess import CalledProcessError
from unittest.mock import Mock, patch

import pytest

from dfu.installed_packages.pacman import get_installed_packages


def test_get_installed_packages_success():
    with patch('subprocess.run') as mocked_run:
        mocked_run.return_value = Mock()
        mocked_run.return_value.stdout = '''
package1
package3
package2
      
    leading_whitespace
    leading_and_trailing_whitespace    
'''
        mocked_run.return_value.returncode = 0
        result = get_installed_packages()
        assert result == ['leading_and_trailing_whitespace', 'leading_whitespace', 'package1', 'package2', 'package3']


def test_get_installed_packages_failure():
    with patch('subprocess.run') as mocked_run:
        mocked_run.return_value = Mock()
        mocked_run.return_value.stdout = 'error\n'
        mocked_run.return_value.returncode = 1

        with pytest.raises(CalledProcessError):
            get_installed_packages()
