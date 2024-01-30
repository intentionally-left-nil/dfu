from importlib.metadata import entry_points
from pathlib import Path

from dfu.api.entrypoint import Entrypoint
from dfu.api.state import State
from dfu.api.store import Store
from dfu.commands.load_config import load_config
from dfu.package.package_config import PackageConfig, find_package_config


def find_package_dir(path: Path = Path.cwd()) -> Path:
    config_path = find_package_config(path)
    if not config_path:
        raise ValueError("No dfu_config.json found in the current directory or any parent directory")
    return config_path.parent


def load_store() -> Store:
    package_dir = find_package_dir()
    package_config = PackageConfig.from_file(package_dir / "dfu_config.json")

    state = State(
        config=load_config(),
        package_dir=package_dir,
        package_config=package_config,
    )
    store = Store(state)
    for entry_point in entry_points().select(group='dfu.plugin'):
        fn: Entrypoint = entry_point.load()
        plugin = fn(store)
        store.plugins.add(plugin)
    return store
