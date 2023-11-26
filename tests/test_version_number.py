from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from dfu.config import Btrfs
from dfu.package.version_number import Config, _get_version_directory


@pytest.fixture
def temp_dir():
    with TemporaryDirectory() as tmp:
        yield tmp


@pytest.fixture
def config(temp_dir):
    return Config(btrfs=Btrfs(snapper_configs=["root"]), package_dir=temp_dir)


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

    def test_version_dir_no_files(self, config):
        (Path(config.package_dir) / "version" / "1").mkdir(parents=True)
        with pytest.raises(ValueError, match="Expected .* to contain files"):
            _get_version_directory(config)

    def test_successful_case(self, config):
        version_dir = Path(config.package_dir) / "version" / "1"
        version_dir.mkdir(parents=True)
        (version_dir / "file.txt").touch()
        assert _get_version_directory(config) == version_dir
