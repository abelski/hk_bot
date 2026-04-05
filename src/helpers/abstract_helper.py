from abc import ABC, abstractmethod


class AbstractHelper(ABC):
    @abstractmethod
    def process_text(self, text: str) -> str: ...
