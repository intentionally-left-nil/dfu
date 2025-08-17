from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import pytest

from dfu.config import Config
from dfu.snapshots.proot import proot
from dfu.snapshots.snapper import Snapper


def test_proot_raises_if_no_snapshots(config: Config) -> None:
    with pytest.raises(ValueError, match="No snapshots to mount"):
        proot(["hello"], config=config, snapshot=MappingProxyType({}))


def test_proot_raises_if_config_mismatch(config: Config) -> None:
    with pytest.raises(ValueError, match="Not all snapshots are listed in the snapper_configs section of the config"):
        proot(["hello"], config=config, snapshot=MappingProxyType({"home": 1, "missing": 2}))


def test_proot_wraps_with_correct_args(config: Config) -> None:
    with patch.object(Snapper, 'get_mountpoint', new=lambda self: Path(f"/{self.snapper_name}")):
        args = proot(["hello", "world"], config=config, snapshot=MappingProxyType({"root": 1, "home": 2, "log": 3}))
        assert args == [
            "sudo",
            "proot",
            "-r",
            "/root/.snapshots/1/snapshot",
            "-b",
            "/home/.snapshots/2/snapshot:/home",
            "-b",
            "/log/.snapshots/3/snapshot:/log",
            "-b",
            "/dev",
            "-b",
            "/proc",
            "hello",
            "world",
        ]


def test_proot_with_cwd(config: Config) -> None:
    with patch.object(Snapper, 'get_mountpoint', new=lambda self: Path(f"/{self.snapper_name}")):
        args = proot(
            ["hello", "world"], config=config, snapshot=MappingProxyType({"root": 1, "home": 2, "log": 3}), cwd="/home"
        )

        assert args == [
            "sudo",
            "proot",
            "-r",
            "/root/.snapshots/1/snapshot",
            "-b",
            "/home/.snapshots/2/snapshot:/home",
            "-b",
            "/log/.snapshots/3/snapshot:/log",
            "-b",
            "/dev",
            "-b",
            "/proc",
            "-w",
            "/home",
            "hello",
            "world",
        ]
