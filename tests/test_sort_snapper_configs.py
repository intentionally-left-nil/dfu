from itertools import permutations
from pathlib import Path

import pytest

from dfu.snapshots.snapper import SnapperConfigInfo
from dfu.snapshots.sort_snapper_configs import sort_snapper_configs


def test_calculate_roots_empty():
    assert sort_snapper_configs([]) == tuple()


def test_calculate_roots_one_node():
    assert sort_snapper_configs([SnapperConfigInfo('test', Path('/test'))]) == ('test',)


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
def test_calculate_roots_root_with_two_subchildren(configs: list[SnapperConfigInfo]):
    assert sort_snapper_configs(configs) == ('root', 'test2', 'test3')


def test_two_independent_roots():
    assert sort_snapper_configs(
        [
            SnapperConfigInfo('test', Path('/test')),
            SnapperConfigInfo('test2', Path('/test2')),
        ]
    ) == ('test2', 'test')


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
def test_complex_case(configs: list[SnapperConfigInfo]):
    assert sort_snapper_configs(configs) == ('root', 'home', 'var', 'another_user', 'me', 'log')
