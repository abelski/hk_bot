import importlib
import inspect
import pkgutil
import os
from src.news.api.abstract_request_command import AbstractRequestCommand


def load_commands() -> list:
    """Return one instance per AbstractRequestCommand subclass found in this package."""
    commands = []
    pkg_dir = os.path.dirname(__file__)
    for _, name, _ in pkgutil.iter_modules([pkg_dir]):
        mod = importlib.import_module(f"{__name__}.{name}")
        for attr_name in dir(mod):
            attr = getattr(mod, attr_name)
            if (
                inspect.isclass(attr)
                and issubclass(attr, AbstractRequestCommand)
                and attr is not AbstractRequestCommand
                and attr.__module__ == f"{__name__}.{name}"
            ):
                commands.append(attr())
    return commands
