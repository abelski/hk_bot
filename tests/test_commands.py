"""
Unit tests for command modules in src/commands/.
"""

import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestWooCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_leaderboard(self):
        from commands.woo_command import run
        entries = [{"rank": 1, "user": {"first_name": "A", "last_name": "B"}, "score": 10}]
        with patch("commands.woo_command._fetch_top3", return_value=entries), \
             patch("commands.woo_command._format_top3", return_value="formatted"):
            result = await run()
        assert result == "formatted"

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.woo_command import run
        with patch("commands.woo_command._fetch_top3", return_value=None):
            result = await run()
        assert "Could not fetch" in result

    def test_has_required_interface(self):
        import commands.woo_command as woo
        assert isinstance(woo.NAME, str)
        assert isinstance(woo.LABEL, str)
        assert callable(woo.run)


class TestHkrCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from commands.hkr_command import run
        review = {"id": 1, "productName": "Test Kite", "brand": "Brand", "productType": "Kite",
                  "writeUp": "Great kite.", "safetyStatus": "safe",
                  "user": {"firstName": "A", "lastName": "B"}, "images": []}
        with patch("commands.hkr_command._fetch", return_value=review), \
             patch("commands.hkr_command._save_state"), \
             patch("commands.hkr_command._format", return_value={"text": "formatted", "photos": []}):
            result = await run()
        assert result == {"text": "formatted", "photos": []}

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.hkr_command import run
        with patch("commands.hkr_command._fetch", return_value=None):
            result = await run()
        assert "Could not fetch" in result

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_same(self):
        from commands.hkr_command import run_if_new
        review = {"id": 42, "productName": "X", "brand": "B", "productType": "T",
                  "writeUp": ".", "safetyStatus": "safe",
                  "user": {"firstName": "X", "lastName": "Y"}, "images": []}
        with patch("commands.hkr_command._fetch", return_value=review), \
             patch("commands.hkr_command._load_state", return_value=42):
            result = await run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_when_new(self):
        from commands.hkr_command import run_if_new
        review = {"id": 99, "productName": "X", "brand": "B", "productType": "T",
                  "writeUp": ".", "safetyStatus": "safe",
                  "user": {"firstName": "X", "lastName": "Y"}, "images": []}
        with patch("commands.hkr_command._fetch", return_value=review), \
             patch("commands.hkr_command._load_state", return_value=1), \
             patch("commands.hkr_command._save_state"), \
             patch("commands.hkr_command._format", return_value={"text": "new review", "photos": []}):
            result = await run_if_new()
        assert result == {"text": "new review", "photos": []}

    def test_has_required_interface(self):
        import commands.hkr_command as cmd
        assert isinstance(cmd.NAME, str)
        assert isinstance(cmd.LABEL, str)
        assert callable(cmd.run)
