import multiprocessing
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from dfu.config import Btrfs
from dfu.package.version_number import (
    Config,
    _get_version_directory,
    _get_version_number,
    _try_create_version_directory,
    get_version_number,
)

TIMEOUT = 5


@pytest.fixture
def temp_dir():
    with TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def config(temp_dir) -> Config:
    return Config(btrfs=Btrfs(snapper_configs=["root"]), package_dir=temp_dir)


def get_version_number_target(config, return_dict, on_get_version_directory, pre_replace_directory):
    version = _get_version_number(
        config, on_get_version_directory=on_get_version_directory, pre_replace_directory=pre_replace_directory
    )
    return_dict["result"] = version


class TestGetVersionNumber:
    def test_get_version_number_no_race(self, config):
        assert get_version_number(config) == 1

    def test_get_version_number_fails_after_5_retries(self, config):
        version_dir = Path(config.package_dir) / "version"
        version_dir.mkdir()
        # Create the subdir, but ensure it's not writeable
        (version_dir / "0").mkdir(parents=True, exist_ok=False)
        (version_dir / "0").chmod(0)
        try:
            with pytest.raises(RuntimeError, match="Too many failures trying to determine the version number"):
                get_version_number(config)
        finally:
            (version_dir / "0").chmod(0o511)
            shutil.rmtree(version_dir)

    def test_get_version_number_race_condition(self, config):
        manager = multiprocessing.Manager()
        p1_return = manager.dict()
        p2_return = manager.dict()

        on_get_version_directory1 = multiprocessing.Event()
        pre_replace_directory1 = multiprocessing.Event()

        on_get_version_directory2 = multiprocessing.Event()
        pre_replace_directory2 = multiprocessing.Event()

        p1 = multiprocessing.Process(
            target=get_version_number_target,
            args=(
                config,
                p1_return,
                on_get_version_directory1,
                pre_replace_directory1,
            ),
        )
        p2 = multiprocessing.Process(
            target=get_version_number_target,
            args=(
                config,
                p2_return,
                on_get_version_directory2,
                pre_replace_directory2,
            ),
        )
        p1.start()
        p2.start()

        if not on_get_version_directory1.wait(timeout=TIMEOUT):
            raise RuntimeError(f"Process 1 failed to get the version directory. Alive? {p1.is_alive()}")
        if not on_get_version_directory2.wait(timeout=TIMEOUT):
            raise RuntimeError(f"Process 2 failed to get the version directory. Alive? {p2.is_alive()}")

        pre_replace_directory1.set()
        p1.join(timeout=TIMEOUT)
        assert p1.is_alive() == False, "Process 1 failed to finish"

        pre_replace_directory2.set()
        p2.join(timeout=TIMEOUT)
        assert p2.is_alive() == False, "Proces 2 failed to finish"
        assert p1_return["result"] == 1
        assert p2_return["result"] == 2


class TestGetVersionDirectory:
    def test_no_package_dir(self, config):
        config.package_dir = str(Path(config.package_dir) / "does_not_exist")
        with pytest.raises(ValueError):
            _get_version_directory(config)

    def test_package_dir_not_dir(self, config):
        file_path = Path(config.package_dir) / "file.txt"
        file_path.touch()
        config.package_dir = str(file_path)
        with pytest.raises(ValueError, match="Expected .* to exist and be a directory"):
            _get_version_directory(config)

    def test_no_subdirs(self, config):
        (Path(config.package_dir) / "version").mkdir()
        with pytest.raises(ValueError, match="Expected exactly one folder in .*"):
            _get_version_directory(config)

    def test_multiple_subdirs(self, config):
        (Path(config.package_dir) / "version" / "1").mkdir(parents=True)
        (Path(config.package_dir) / "version" / "2").mkdir(parents=True)
        with pytest.raises(ValueError, match="Expected exactly one folder in .*"):
            _get_version_directory(config)

    def test_version_dir_not_numeric(self, config):
        (Path(config.package_dir) / "version" / "not_numeric").mkdir(parents=True)
        with pytest.raises(ValueError, match="Expected .* to be a number"):
            _get_version_directory(config)

    def test_successful_case(self, config):
        version_dir = Path(config.package_dir) / "version" / "1"
        version_dir.mkdir(parents=True)
        (version_dir / "file.txt").touch()
        assert _get_version_directory(config) == version_dir


class TestTryCreateVersionDirectory:
    def test_version_dir_exists(self, config):
        version_dir = Path(config.package_dir) / "version"
        version_dir.mkdir(parents=True, exist_ok=True)
        (version_dir / "42").mkdir(parents=True)
        _try_create_version_directory(config)

        assert not any(path.name.startswith('version_') for path in Path(config.package_dir).iterdir())
        assert (Path(config.package_dir) / "version" / "42").exists()

    def test_version_dir_not_exists(self, config):
        _try_create_version_directory(config)

        assert (Path(config.package_dir) / "version" / "0").exists()
        assert not any(path.name.startswith('version_') for path in Path(config.package_dir).iterdir())
