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


class TestTranslateHelper:
    def test_returns_translated_text(self):
        from commands.helpers.translate import translate_to_russian
        with patch("commands.helpers.translate._translate_chunk", return_value="привет"):
            result = translate_to_russian("hello")
        assert result == "привет"

    def test_falls_back_on_chunk_failure(self):
        from commands.helpers.translate import translate_to_russian
        with patch("commands.helpers.translate._translate_chunk", return_value=None):
            result = translate_to_russian("hello")
        assert result == "hello"

    def test_returns_empty_string_unchanged(self):
        from commands.helpers.translate import translate_to_russian
        assert translate_to_russian("") == ""

    def test_splits_long_text_into_chunks(self):
        from commands.helpers.translate import _split
        long = "A" * 400 + "\n\n" + "B" * 400
        chunks = _split(long)
        assert len(chunks) == 2
        assert all(len(c) <= 500 for c in chunks)


class TestWindguruCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from commands.windguru_command import run
        from datetime import datetime, timezone
        # tz_offset=0 so "local" == UTC, making slot dates deterministic
        spots = [{"id": 137635, "name": "Lithuania - Svencele", "tz_offset": 0}]
        now = datetime.now(timezone.utc)
        init = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        # hours 8, 12, 16 UTC — always within the 6-22 local day window
        mock_data = {"fcst": {
            "initdate": init,
            "hours": [8, 12, 16],
            "WINDSPD": [10.0, 15.0, 20.0],
            "GUST": [13.0, 19.0, 26.0],
            "WINDDIR": [220, 225, 200],
        }}
        with patch("commands.windguru_command._load_spots", return_value=spots), \
             patch("commands.windguru_command._fetch", return_value=mock_data):
            result = await run()
        assert "Lithuania - Svencele" in result
        assert "kn" in result
        assert "Сегодня" in result

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.windguru_command import run
        spots = [{"id": 137635, "name": "Lithuania - Svencele"}]
        with patch("commands.windguru_command._load_spots", return_value=spots), \
             patch("commands.windguru_command._fetch", return_value=None):
            result = await run()
        assert "Lithuania - Svencele" in result
        assert "прогноз" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_message_when_no_spots_configured(self):
        from commands.windguru_command import run
        with patch("commands.windguru_command._load_spots", return_value=[]):
            result = await run()
        assert "config.json" in result

    def test_has_required_interface(self):
        import commands.windguru_command as cmd
        assert isinstance(cmd.NAME, str)
        assert isinstance(cmd.LABEL, str)
        assert callable(cmd.run)

    def test_deg_to_dir(self):
        from commands.windguru_command import _deg_to_dir
        assert _deg_to_dir(0) == "N"
        assert _deg_to_dir(180) == "S"
        assert _deg_to_dir(225) == "SW"

    def test_wind_color(self):
        from commands.windguru_command import _wind_color
        assert _wind_color(5) == "⚪"
        assert _wind_color(10) == "🔵"
        assert _wind_color(16) == "🟢"
        assert _wind_color(24) == "🟡"
        assert _wind_color(35) == "🔴"

    def test_wind_stars(self):
        from commands.windguru_command import _wind_stars
        assert _wind_stars(5) == "·"
        assert _wind_stars(10) == "⭐"
        assert _wind_stars(15) == "⭐⭐⭐"
        assert _wind_stars(20) == "⭐⭐⭐⭐⭐"
        assert _wind_stars(28) == "⭐⭐⭐"
        assert _wind_stars(35) == "⭐"
