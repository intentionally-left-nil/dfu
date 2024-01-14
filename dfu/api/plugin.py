from abc import ABC, abstractmethod
from enum import StrEnum, auto
from typing import Literal


class Event(StrEnum):
    TARGET_BRANCH_FINALIZED = auto()


class DfuPlugin(ABC):
    @abstractmethod
    def handle(self, event: Event):
        pass
