import json
import tempfile
from dataclasses import dataclass, field

import dataclass_wizard.errors
import pytest

from dfu.package.package_config import PackageConfig, Snapshot


@dataclass
class ValidConfigTest:
    test_id: str
    name: str = "expected_name"
    description: str | None = "expected_description"
    snapshots: list[dict[str, dict]] = field(default_factory=list)


valid_config_tests = [
    ValidConfigTest(test_id="empty"),
    ValidConfigTest(test_id="one snapshot with a pre_id", snapshots=[{"root": {"pre_id": 1}}]),
    ValidConfigTest(test_id="one snapshot with a pre and post id", snapshots=[{"root": {"pre_id": 1, "post_id": 2}}]),
    ValidConfigTest(
        test_id="one snapshot with two volumes, both having a pre id",
        snapshots=[{"root": {"pre_id": 1}, "home": {"pre_id": 2}}],
    ),
    ValidConfigTest(
        test_id="one snapshot with a full root, but only a pre id for home",
        snapshots=[{"root": {"pre_id": 1, "post_id": 2}, "home": {"pre_id": 3}}],
    ),
    ValidConfigTest(
        test_id="one snapshot with two volumes, both having a pre and post id",
        snapshots=[{"root": {"pre_id": 1, "post_id": 2}, "home": {"pre_id": 3, "post_id": 4}}],
    ),
    ValidConfigTest(
        test_id="two snapshots with a pre_id", snapshots=[{"root": {"pre_id": 1}}, {"root": {"pre_id": 2}}]
    ),
    ValidConfigTest(
        test_id="two snapshots where the first one is full",
        snapshots=[{"root": {"pre_id": 1, "post_id": 2}}, {"root": {"pre_id": 3}}],
    ),
    ValidConfigTest(
        test_id="two snapshots where the directories are different",
        snapshots=[{"root": {"pre_id": 1, "post_id": 2}}, {"home": {"pre_id": 3, "post_id": 4}}],
    ),
]


@pytest.mark.parametrize("test", valid_config_tests, ids=[t.test_id for t in valid_config_tests])
def test_valid_configs(test: ValidConfigTest):
    json_data = json.dumps(test.__dict__)
    actual = PackageConfig.from_json(json_data)
    expected_snapshots = [
        {k: Snapshot(pre_id=v['pre_id'], post_id=v.get('post_id', None)) for k, v in item.items()}
        for item in test.snapshots
    ]
    expected = PackageConfig(name=test.name, description=test.description, snapshots=expected_snapshots)
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
