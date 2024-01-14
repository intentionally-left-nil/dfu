from abc import ABC, abstractmethod


class DfuPlugin(ABC):
    @abstractmethod
    def handle(self):
        pass
