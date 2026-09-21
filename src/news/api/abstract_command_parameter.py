from abc import ABC, abstractmethod


class AbstractCommandParameter(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def description(self) -> str: ...
