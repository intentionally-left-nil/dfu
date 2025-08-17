from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class Event:
    pass


@dataclass
class UpdateInstalledDependenciesEvent(Event):
    from_index: int
    to_index: int


@dataclass
class InstallDependenciesEvent(Event):
    confirm: bool
    dry_run: bool


@dataclass
class UninstallDependenciesEvent(Event):
    confirm: bool
    dry_run: bool


class DfuPlugin(ABC):
    @abstractmethod
    def handle(self, event: Event) -> None:  # pragma: no cover
        pass
