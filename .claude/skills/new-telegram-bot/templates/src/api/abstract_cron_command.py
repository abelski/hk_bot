from abc import ABC, abstractmethod
from typing import ClassVar


class AbstractCronCommand(ABC):
    """Command executed on a recurring cron schedule."""

    NAME: ClassVar[str]

    @abstractmethod
    async def run(self): ...
