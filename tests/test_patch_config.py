import json
from pathlib import Path
from tempfile import TemporaryDirectory

from dfu.package.patch_config import PatchConfig


def test_patch_config_from_file() -> None:
    """Test loading PatchConfig from a JSON file."""
    config_data = {"pack_version": 2, "version": "1.0.0"}

    with TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        config = PatchConfig.from_file(config_path)
        assert config.pack_version == 2
        assert config.version == "1.0.0"


def test_patch_config_from_file_missing() -> None:
    """Test loading PatchConfig from a missing file returns defaults."""
    with TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "missing_config.json"

        config = PatchConfig.from_file(config_path)
        assert config.pack_version == 1
        assert config.version == "0.0.4"


def test_patch_config_serialization() -> None:
    """Test that PatchConfig can be serialized and deserialized."""
    original_config = PatchConfig(pack_version=2, version="1.5.0")

    with TemporaryDirectory() as temp_dir:
        config_path = Path(temp_dir) / "config.json"
        original_config.write(config_path)

        loaded_config = PatchConfig.from_file(config_path)
        assert loaded_config == original_config
