from dfu.api import Event, Store
from dfu.package.install import Install


def begin_install(store: Store):
    if store.state.install is not None:
        raise ValueError('Installation is already in progress. Run dfu install --continue to continue installation.')

    store.state = store.state.update(install=Install())
    continue_install(store)


def continue_install(store: Store):
    if store.state.install is None:
        raise ValueError('There is no in-progress installation. Run dfu install --begin to begin installation.')

    if not store.state.install.installed_dependencies:
        store.dispatch(Event.INSTALL_DEPENDENCIES)
        store.state = store.state.update(install=store.state.install.update(installed_dependencies=True))


def abort_install(store: Store):
    store.state = store.state.update(install=None)
