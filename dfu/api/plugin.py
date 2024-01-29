from abc import ABC, abstractmethod
from enum import StrEnum, auto


class Event(StrEnum):
    UPDATE_INSTALLED_DEPENDENCIES = auto()
    INSTALL_DEPENDENCIES = auto()
    UNINSTALL_DEPENDENCIES = auto()


class DfuPlugin(ABC):
    @abstractmethod
    def handle(self, event: Event, **kwargs):  # pragma: no cover
        pass
