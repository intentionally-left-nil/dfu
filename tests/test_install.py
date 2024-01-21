from dfu.package.install import Install


def test_install():
    install = Install()
    assert install.installed_dependencies == False
    install = install.update(installed_dependencies=True)
    assert install.installed_dependencies == True
