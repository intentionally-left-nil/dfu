import pytest

from dfu.snapshots.snapper_diff import FileChangeAction, SnapperDiff


@pytest.mark.parametrize(
    "status, expected_diff",
    [
        ("+..... test.txt", SnapperDiff("test.txt", FileChangeAction.created, False)),
        ("-..... deleted.txt", SnapperDiff("deleted.txt", FileChangeAction.deleted, False)),
        ("c..... modified.txt", SnapperDiff("modified.txt", FileChangeAction.modified, False)),
        ("t..... type_changed.txt", SnapperDiff("type_changed.txt", FileChangeAction.type_changed, False)),
        (".p.... no_change.txt", SnapperDiff("no_change.txt", FileChangeAction.no_change, True)),
        ("+p.... created_p.txt", SnapperDiff("created_p.txt", FileChangeAction.created, True)),
        ("+..g.. created_g.txt", SnapperDiff("created_g.txt", FileChangeAction.created, True)),
        ("+.u... created_u.txt", SnapperDiff("created_u.txt", FileChangeAction.created, True)),
        ("+pug.. created_pug.txt", SnapperDiff("created_pug.txt", FileChangeAction.created, True)),
        ("+pu... created_pu.txt", SnapperDiff("created_pu.txt", FileChangeAction.created, True)),
        ("+.ug.. created_ug.txt", SnapperDiff("created_ug.txt", FileChangeAction.created, True)),
        ("+....a created_a.txt", SnapperDiff("created_a.txt", FileChangeAction.created, False)),
    ],
)
def test_from_status(status, expected_diff):
    diff = SnapperDiff.from_status(status)
    assert diff == expected_diff


@pytest.mark.parametrize(
    "status",
    [
        "invalid status",
        "++..... invalid.txt",
        "+pugx invalid.txt",
        "+.....",
    ],
)
def test_from_status_invalid_format(status):
    with pytest.raises(ValueError):
        SnapperDiff.from_status(status)
