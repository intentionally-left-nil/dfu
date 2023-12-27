from itertools import permutations
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from dfu.config import Btrfs, Config
from dfu.config.default_config import get_default_config
from dfu.snapshots.snapper import SnapperConfigInfo


@pytest.fixture(autouse=True)
def mock_get_configs() -> Generator[MagicMock, None, None]:
    with patch('dfu.snapshots.snapper.Snapper.get_configs') as mock:
        yield mock


def test_calculate_roots_empty(mock_get_configs):
    mock_get_configs.return_value = []
    assert get_default_config() == Config(btrfs=Btrfs(snapper_configs=[]))


def test_calculate_roots_one_node(mock_get_configs):
    mock_get_configs.return_value = [SnapperConfigInfo('test', Path('/test'))]
    assert get_default_config() == Config(btrfs=Btrfs(snapper_configs=['test']))


@pytest.mark.parametrize(
    'configs',
    permutations(
        [
            SnapperConfigInfo('root', Path('/')),
            SnapperConfigInfo('test2', Path('/test2')),
            SnapperConfigInfo('test3', Path('/test3')),
        ]
    ),
)
def test_calculate_roots_root_with_two_subchildren(configs: list[SnapperConfigInfo], mock_get_configs):
    mock_get_configs.return_value = configs
    assert get_default_config() == Config(btrfs=Btrfs(snapper_configs=['root', 'test2', 'test3']))


def test_two_independent_roots(mock_get_configs):
    mock_get_configs.return_value = [
        SnapperConfigInfo('test', Path('/test')),
        SnapperConfigInfo('test2', Path('/test2')),
    ]
    assert get_default_config() == Config(btrfs=Btrfs(snapper_configs=['test2', 'test']))


@pytest.mark.parametrize(
    'configs',
    list(
        permutations(
            [
                SnapperConfigInfo('root', Path('/')),
                SnapperConfigInfo('var', Path('/var')),
                SnapperConfigInfo('log', Path('/var/log')),
                SnapperConfigInfo('home', Path('/home')),
                SnapperConfigInfo('me', Path('/home/me')),
                SnapperConfigInfo('another_user', Path('/home/another_user')),
            ]
        )
    ),
)
def test_complex_case(configs: list[SnapperConfigInfo], mock_get_configs):
    mock_get_configs.return_value = configs
    assert get_default_config() == Config(
        btrfs=Btrfs(snapper_configs=['root', 'home', 'var', 'another_user', 'me', 'log'])
    )
