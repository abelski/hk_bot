"""
Unit tests for src/config_loader.py.
"""

import json
import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestLoadConfig:
    def test_loads_valid_config(self, tmp_path):
        cfg = {"mappings": [{"command": "woo", "chat_id": "-100111", "cron": "0 23 * * *"}]}
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(cfg))

        import config_loader
        original = config_loader._CONFIG_PATH
        config_loader._CONFIG_PATH = str(config_file)
        try:
            result = config_loader.load_config()
        finally:
            config_loader._CONFIG_PATH = original

        assert result["mappings"][0]["command"] == "woo"
        assert result["mappings"][0]["chat_id"] == "-100111"
        assert result["mappings"][0]["cron"] == "0 23 * * *"

    def test_returns_empty_mappings_when_file_missing(self, tmp_path):
        import config_loader
        original = config_loader._CONFIG_PATH
        config_loader._CONFIG_PATH = str(tmp_path / "nonexistent.json")
        try:
            result = config_loader.load_config()
        finally:
            config_loader._CONFIG_PATH = original

        assert result == {"mappings": []}

    def test_loads_multiple_mappings(self, tmp_path):
        cfg = {
            "mappings": [
                {"command": "woo", "chat_id": "-100111", "cron": "0 23 * * *"},
                {"command": "woo", "chat_id": "-100222"},
            ]
        }
        config_file = tmp_path / "config.json"
        config_file.write_text(json.dumps(cfg))

        import config_loader
        original = config_loader._CONFIG_PATH
        config_loader._CONFIG_PATH = str(config_file)
        try:
            result = config_loader.load_config()
        finally:
            config_loader._CONFIG_PATH = original

        assert len(result["mappings"]) == 2
