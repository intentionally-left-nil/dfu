from dfu.package.uninstall import Uninstall


def test_install():
    uninstall = Uninstall()
    assert uninstall.removed_dependencies == False
    install = uninstall.update(removed_dependencies=True)
    assert install.removed_dependencies == True
