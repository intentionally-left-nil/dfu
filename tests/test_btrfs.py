from unittest.mock import MagicMock, patch

import pytest

from dfu.snapshots.btrfs import get_all_subvolumes


@patch('subprocess.run')
def test_get_all_subvolumes(mock_run: MagicMock):
    mock_run.return_value.stdout = '''\
/
/home
/var

'''
    assert get_all_subvolumes() == ['/', '/home', '/var']
