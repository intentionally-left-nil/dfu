from itertools import permutations
from pathlib import Path

import pytest

from dfu.config.default_config import Node, SnapperConfigInfo, calculate_roots


def test_calculate_roots_empty():
    assert calculate_roots([]) == []


def test_calculate_roots_one_node():
    assert calculate_roots([SnapperConfigInfo('test', Path('/test'))]) == [
        Node(SnapperConfigInfo('test', Path('/test')))
    ]


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
    assert calculate_roots(configs) == [
        Node(
            SnapperConfigInfo('root', Path('/')),
            children=[
                Node(SnapperConfigInfo('test2', Path('/test2'))),
                Node(SnapperConfigInfo('test3', Path('/test3'))),
            ],
        )
    ]


def test_two_independent_roots():
    assert calculate_roots(
        [
            SnapperConfigInfo('test', Path('/test')),
            SnapperConfigInfo('test2', Path('/test2')),
        ]
    ) == [
        Node(SnapperConfigInfo('test2', Path('/test2'))),
        Node(SnapperConfigInfo('test', Path('/test'))),
    ]


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
    assert calculate_roots(configs) == [
        Node(
            SnapperConfigInfo('root', Path('/')),
            children=[
                Node(
                    SnapperConfigInfo('home', Path('/home')),
                    children=[
                        Node(SnapperConfigInfo('another_user', Path('/home/another_user'))),
                        Node(SnapperConfigInfo('me', Path('/home/me'))),
                    ],
                ),
                Node(
                    SnapperConfigInfo('var', Path('/var')), children=[Node(SnapperConfigInfo('log', Path('/var/log')))]
                ),
            ],
        )
    ]
