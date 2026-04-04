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
