from dfu.package.dfu_diff import DfuDiff


def test_dfu_diff():
    diff = DfuDiff(from_index=0, to_index=1)
    assert diff.from_index == 0
    assert diff.to_index == 1
    assert diff.updated_installed_programs == False

    diff = diff.update(updated_installed_programs=True)
    assert diff.updated_installed_programs == True
