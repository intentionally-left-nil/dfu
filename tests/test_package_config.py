import tempfile

import dataclass_wizard.errors
import pytest

from dfu.package.package_config import PackageConfig, State


def test_valid_config():
    json_data = '{"name": "expected_name", "description": "expected_description", "state": "NEW"}'
    actual = PackageConfig.from_json(json_data)
    expected = PackageConfig(name='expected_name', description='expected_description', state=State.new)
    assert actual == expected


def test_from_file():
    json_data = '{"name": "expected_name", "description": "expected_description", "state": "NEW"}'
    with tempfile.NamedTemporaryFile("w") as f:
        f.write(json_data)
        f.flush()
        actual = PackageConfig.from_file(f.name)
        expected = PackageConfig(name='expected_name', description='expected_description', state=State.new)
        assert actual == expected


def test_invalid_state():
    invalid_json_data = '{"name": 123, "description": "expected_description", "state": "BOGUS_STATE"}'
    with pytest.raises(ValueError):
        PackageConfig.from_json(invalid_json_data)


def test_missing_field():
    invalid_json_data = '{"name": "expected_name", "state": "NEW"}'
    with pytest.raises(dataclass_wizard.errors.MissingFields):
        PackageConfig.from_json(invalid_json_data)
