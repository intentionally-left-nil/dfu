from dfu.package.dfu_diff import DfuDiff


def test_dfu_diff():
    diff = DfuDiff()
    assert diff.created_placeholders == False
    assert diff.updated_installed_programs == False
    assert diff.base_branch == None
    assert diff.target_branch == None
