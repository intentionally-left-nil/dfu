from dfu.api import Event, Store


def begin_install(store: Store):
    pass


def continue_install(store: Store):
    store.dispatch(Event.INSTALL_DEPENDENCIES)


def abort_install(store: Store):
    pass
