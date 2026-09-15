from abc import ABC, abstractmethod
from typing import ClassVar, List


class AbstractRequestCommand(ABC):
    """Command answered in direct messages. May declare zero or more parameters."""

    NAME: ClassVar[str]
    LABEL: ClassVar[str]
    parameters: ClassVar[List] = []

    @abstractmethod
    async def run(self): ...
