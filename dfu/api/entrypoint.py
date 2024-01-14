from typing import Callable

from dfu.api.plugin import DfuPlugin
from dfu.api.store import Store

Entrypoint = Callable[[Store], DfuPlugin]
