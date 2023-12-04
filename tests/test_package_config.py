import tempfile

import dataclass_wizard.errors
import pytest

from dfu.package.package_config import PackageConfig, Snapshot


def test_valid_config():
    json_data = '{"name": "expected_name", "description": "expected_description", "snapshots": {"root": {"pre_id": 1, "post_id": 2}}}'
    actual = PackageConfig.from_json(json_data)
    expected = PackageConfig(
        name='expected_name',
        description='expected_description',
        snapshots={'root': Snapshot(pre_id=1, post_id=2)},
    )
    assert actual == expected


def test_from_file():
    json_data = '{"name": "expected_name", "description": "expected_description"}'
    with tempfile.NamedTemporaryFile("w") as f:
        f.write(json_data)
        f.flush()
        actual = PackageConfig.from_file(f.name)
        expected = PackageConfig(name='expected_name', description='expected_description')
        assert actual == expected


def test_missing_field():
    invalid_json_data = '{"name": "expected_name"}'
    with pytest.raises(dataclass_wizard.errors.MissingFields):
        PackageConfig.from_json(invalid_json_data)


def test_write_config():
    config = PackageConfig(name='expected_name', description='expected_description')
    with tempfile.NamedTemporaryFile("w") as f:
        config.write(f.name)
        f.flush()
        actual = PackageConfig.from_file(f.name)
        expected = PackageConfig(name='expected_name', description='expected_description')
        assert actual == expected
