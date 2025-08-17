from itertools import permutations
from pathlib import Path

import pytest

from dfu.snapshots.snapper import SnapperConfigInfo, SnapperName
from dfu.snapshots.sort_snapper_configs import sort_snapper_configs


def test_calculate_roots_empty() -> None:
    assert sort_snapper_configs([]) == tuple()


def test_calculate_roots_one_node() -> None:
    assert sort_snapper_configs([SnapperConfigInfo(SnapperName('test'), Path('/test'))]) == (SnapperName('test'),)


@pytest.mark.parametrize(
    'configs',
    permutations(
        [
            SnapperConfigInfo(SnapperName('root'), Path('/')),
            SnapperConfigInfo(SnapperName('test2'), Path('/test2')),
            SnapperConfigInfo(SnapperName('test3'), Path('/test3')),
        ]
    ),
)
def test_calculate_roots_root_with_two_subchildren(configs: list[SnapperConfigInfo]) -> None:
    assert sort_snapper_configs(configs) == (SnapperName('root'), SnapperName('test2'), SnapperName('test3'))


def test_two_independent_roots() -> None:
    assert sort_snapper_configs(
        [
            SnapperConfigInfo(SnapperName('test'), Path('/test')),
            SnapperConfigInfo(SnapperName('test2'), Path('/test2')),
        ]
    ) == (SnapperName('test2'), SnapperName('test'))


@pytest.mark.parametrize(
    'configs',
    list(
        permutations(
            [
                SnapperConfigInfo(SnapperName('root'), Path('/')),
                SnapperConfigInfo(SnapperName('var'), Path('/var')),
                SnapperConfigInfo(SnapperName('log'), Path('/var/log')),
                SnapperConfigInfo(SnapperName('home'), Path('/home')),
                SnapperConfigInfo(SnapperName('me'), Path('/home/me')),
                SnapperConfigInfo(SnapperName('another_user'), Path('/home/another_user')),
            ]
        )
    ),
)
def test_complex_case(configs: list[SnapperConfigInfo]) -> None:
    assert sort_snapper_configs(configs) == (
        SnapperName('root'),
        SnapperName('home'),
        SnapperName('var'),
        SnapperName('another_user'),
        SnapperName('me'),
        SnapperName('log'),
    )
