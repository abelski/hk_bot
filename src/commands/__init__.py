import importlib
import pkgutil
import os


def load_commands():
    """Return list of command modules found in this package directory."""
    commands = []
    pkg_dir = os.path.dirname(__file__)
    for _, name, _ in pkgutil.iter_modules([pkg_dir]):
        mod = importlib.import_module(f"commands.{name}")
        if hasattr(mod, "NAME") and hasattr(mod, "LABEL") and hasattr(mod, "run"):
            commands.append(mod)
    return commands
