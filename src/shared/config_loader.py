import json

from src.shared.paths import ROOT

_CONFIG_PATH = ROOT / "config.json"


def load_config() -> dict:
    """Load config.json. Returns empty mappings dict if file is missing."""
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {"mappings": []}
