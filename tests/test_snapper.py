import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from dfu.snapshots.snapper import Snapper, SnapperConfigInfo
from dfu.snapshots.snapper_diff import FileChangeAction, SnapperDiff


@pytest.fixture
def snapper_instance():
    return Snapper('test')


@patch('subprocess.run')
def test_get_mountpoint_success(mock_run):
    mock_run.return_value = Mock(stdout='{"SUBVOLUME": "/test"}')
    snapper = Snapper('test')
    assert snapper.get_mountpoint() == Path('/test')


@patch('subprocess.run')
def test_get_mountpoint_no_subvolume(mock_run):
    mock_run.return_value = Mock(stdout='{}')
    snapper = Snapper('test')
    with pytest.raises(KeyError):
        snapper.get_mountpoint()


@patch('subprocess.run')
def test_get_mountpoint_invalid_json(mock_run):
    mock_run.return_value = Mock(stdout='{')
    snapper = Snapper('test')
    with pytest.raises(json.JSONDecodeError):
        snapper.get_mountpoint()


@patch('subprocess.run')
def test_get_mountpoint_subprocess_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd')
    snapper = Snapper('test')
    with pytest.raises(subprocess.CalledProcessError):
        snapper.get_mountpoint()


@patch('subprocess.run')
def test_create_pre_snapshot_success(mock_run):
    mock_run.return_value = Mock(stdout='1\n')
    snapper = Snapper('test')
    assert snapper.create_pre_snapshot('description') == 1


@patch('subprocess.run')
def test_create_pre_snapshot_subprocess_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd')
    snapper = Snapper('test')
    with pytest.raises(subprocess.CalledProcessError):
        snapper.create_pre_snapshot('description')


@patch('subprocess.run')
def test_create_pre_snapshot_invalid_output(mock_run):
    mock_run.return_value = Mock(stdout='not a number\n')
    snapper = Snapper('test')
    with pytest.raises(ValueError):
        snapper.create_pre_snapshot('description')


@patch('subprocess.run')
def test_create_post_snapshot_success(mock_run):
    mock_run.return_value = Mock(stdout='2\n')
    snapper = Snapper('test')
    assert snapper.create_post_snapshot(1, 'description') == 2


@patch('subprocess.run')
def test_create_post_snapshot_subprocess_error(mock_run):
    mock_run.side_effect = subprocess.CalledProcessError(1, 'cmd')
    snapper = Snapper('test')
    with pytest.raises(subprocess.CalledProcessError):
        snapper.create_post_snapshot(1, 'description')


@patch('subprocess.run')
def test_create_post_snapshot_invalid_output(mock_run):
    mock_run.return_value = Mock(stdout='not a number\n')
    snapper = Snapper('test')
    with pytest.raises(ValueError):
        snapper.create_post_snapshot(1, 'description')


@patch('subprocess.run')
def test_get_delta_success(mock_run, snapper_instance):
    mock_run.return_value = MagicMock(stdout='+..... test\n')
    expected_result = [SnapperDiff(path='test', action=FileChangeAction.created, permissions_changed=False)]
    result = snapper_instance.get_delta(1, 2)
    assert result == expected_result


@patch('subprocess.run')
def test_get_delta_multiple_lines(mock_run, snapper_instance):
    mock_run.return_value = MagicMock(stdout='+..... test1\n-..... test2\n')
    expected_result = [
        SnapperDiff(path='test1', action=FileChangeAction.created, permissions_changed=False),
        SnapperDiff(path='test2', action=FileChangeAction.deleted, permissions_changed=False),
    ]
    result = snapper_instance.get_delta(1, 2)
    assert result == expected_result


@patch('subprocess.run')
def test_get_delta_empty_string(mock_run, snapper_instance):
    mock_run.return_value = MagicMock(stdout='')
    expected_result = []
    result = snapper_instance.get_delta(1, 2)
    assert result == expected_result


@patch('subprocess.run')
def test_get_delta_different_actions_and_permissions(mock_run, snapper_instance):
    mock_run.return_value = MagicMock(stdout='+..... test1\n-..... test2\nc..... test3\n')
    expected_result = [
        SnapperDiff(path='test1', action=FileChangeAction.created, permissions_changed=False),
        SnapperDiff(path='test2', action=FileChangeAction.deleted, permissions_changed=False),
        SnapperDiff(path='test3', action=FileChangeAction.modified, permissions_changed=False),
    ]
    result = snapper_instance.get_delta(1, 2)
    assert result == expected_result


@patch('subprocess.run')
def test_get_snapshot_path(mock_run):
    mock_run.return_value = Mock(stdout='{"SUBVOLUME": "/test"}')
    snapper = Snapper('test')
    assert snapper.get_snapshot_path(1) == Path('/test/.snapshots/1/snapshot')


@patch('subprocess.run')
def test_get_configs(mock_run):
    mock_run.return_value = Mock(stdout='{"configs": [{"config": "root", "subvolume": "/home"}]}')
    assert Snapper.get_configs() == [SnapperConfigInfo(name="root", mountpoint=Path("/home"))]


@patch('subprocess.run')
def test_get_configs_requires_sudo(mock_run: MagicMock):
    def mock_subprocess_run(cmd, *args, **kwargs):
        if 'sudo' in cmd:
            return Mock(stdout='{"configs": [{"config": "root", "subvolume": "/home"}]}')
        else:
            return Mock(stdout='')

    mock_run.side_effect = mock_subprocess_run
    assert Snapper.get_configs() == [SnapperConfigInfo(name="root", mountpoint=Path("/home"))]
