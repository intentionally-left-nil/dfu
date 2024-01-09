from pathlib import Path
from unittest.mock import patch

import pytest

from dfu.config import Config
from dfu.snapshots.proot import proot
from dfu.snapshots.snapper import Snapper


def test_proot_raises_if_no_snapshots(config: Config):
    with pytest.raises(ValueError, match="No snapshots to mount"):
        proot(["hello"], config=config, snapshot={})


def test_proot_raises_if_config_mismatch(config: Config):
    with pytest.raises(ValueError, match="Not all snapshots are listed in the snapper_configs section of the config"):
        proot(["hello"], config=config, snapshot={"home": 1, "missing": 2})


def test_proot_wraps_with_correct_args(config: Config):
    with patch.object(Snapper, 'get_mountpoint', new=lambda self: Path(f"/{self.snapper_name}")):
        args = proot(["hello", "world"], config=config, snapshot={"root": 1, "home": 2, "log": 3})
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
