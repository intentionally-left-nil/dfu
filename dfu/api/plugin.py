from abc import ABC, abstractmethod
from enum import StrEnum, auto


class Event(StrEnum):
    TARGET_BRANCH_FINALIZED = auto()


class DfuPlugin(ABC):
    @abstractmethod
    def handle(self, event: Event):  # pragma: no cover
        pass