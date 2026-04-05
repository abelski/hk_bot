from abc import ABC, abstractmethod
from typing import ClassVar


class AbstractNewsCommand(ABC):
    """Command that tracks what was last sent per chat and only sends when the answer changes."""

    NAME: ClassVar[str]

    @abstractmethod
    async def run_if_new(self): ...
