from dfu.package.dfu_diff import DfuDiff


def test_dfu_diff():
    diff = DfuDiff(from_index=0, to_index=1)
    assert diff.from_index == 0
    assert diff.to_index == 1
    assert diff.created_placeholders == False
    assert diff.updated_installed_programs == False

    diff = diff.update(created_placeholders=True, updated_installed_programs=True)
    assert diff.created_placeholders == True
    assert diff.updated_installed_programs == True
