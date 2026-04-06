"""
Unit tests for command classes in src/commands/.
"""

import sys
import os
import pytest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestWooCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_leaderboard(self):
        from commands.woo_command import WooCommand
        entries = [{"rank": 1, "user": {"first_name": "A", "last_name": "B"}, "score": 10}]
        with patch("commands.woo_command._fetch_top3", return_value=entries), \
             patch("commands.woo_command._format_top3", return_value="formatted"):
            result = await WooCommand().run()
        assert result == "formatted"

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.woo_command import WooCommand
        with patch("commands.woo_command._fetch_top3", return_value=None):
            result = await WooCommand().run()
        assert "Could not fetch" in result

    def test_has_required_interface(self):
        from commands.woo_command import WooCommand
        from api.abstract_request_command import AbstractRequestCommand
        from api.abstract_cron_command import AbstractCronCommand
        assert issubclass(WooCommand, AbstractRequestCommand)
        assert issubclass(WooCommand, AbstractCronCommand)
        assert isinstance(WooCommand.NAME, str)
        assert isinstance(WooCommand.LABEL, str)
        assert callable(WooCommand().run)


class TestHkrCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from commands.hkr_command import HkrCommand
        review = {"id": 1, "productName": "Test Kite", "brand": "Brand", "productType": "Kite",
                  "writeUp": "Great kite.", "safetyStatus": "safe",
                  "user": {"firstName": "A", "lastName": "B"}, "images": []}
        with patch("commands.hkr_command._fetch", return_value=review), \
             patch("commands.hkr_command._save_state"), \
             patch("commands.hkr_command._format", return_value={"text": "formatted", "photos": []}):
            result = await HkrCommand().run()
        assert result == {"text": "formatted", "photos": []}

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.hkr_command import HkrCommand
        with patch("commands.hkr_command._fetch", return_value=None):
            result = await HkrCommand().run()
        assert "Could not fetch" in result

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_same(self):
        from commands.hkr_command import HkrCommand
        review = {"id": 42, "productName": "X", "brand": "B", "productType": "T",
                  "writeUp": ".", "safetyStatus": "safe",
                  "user": {"firstName": "X", "lastName": "Y"}, "images": []}
        with patch("commands.hkr_command._fetch", return_value=review), \
             patch("commands.hkr_command._load_state", return_value=42):
            result = await HkrCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_when_new(self):
        from commands.hkr_command import HkrCommand
        review = {"id": 99, "productName": "X", "brand": "B", "productType": "T",
                  "writeUp": ".", "safetyStatus": "safe",
                  "user": {"firstName": "X", "lastName": "Y"}, "images": []}
        with patch("commands.hkr_command._fetch", return_value=review), \
             patch("commands.hkr_command._load_state", return_value=1), \
             patch("commands.hkr_command._save_state"), \
             patch("commands.hkr_command._format", return_value={"text": "new review", "photos": []}):
            result = await HkrCommand().run_if_new()
        assert result == {"text": "new review", "photos": []}

    def test_has_required_interface(self):
        from commands.hkr_command import HkrCommand
        from api.abstract_request_command import AbstractRequestCommand
        from api.abstract_news_command import AbstractNewsCommand
        assert issubclass(HkrCommand, AbstractRequestCommand)
        assert issubclass(HkrCommand, AbstractNewsCommand)
        assert isinstance(HkrCommand.NAME, str)
        assert isinstance(HkrCommand.LABEL, str)
        assert callable(HkrCommand().run)
        assert callable(HkrCommand().run_if_new)


class TestTranslateHelper:
    def test_returns_translated_text(self):
        from helpers.translation_helper import translate_to_russian
        with patch("helpers.translation_helper._translate_chunk", return_value="привет"):
            result = translate_to_russian("hello")
        assert result == "привет"

    def test_falls_back_on_chunk_failure(self):
        from helpers.translation_helper import translate_to_russian
        with patch("helpers.translation_helper._translate_chunk", return_value=None):
            result = translate_to_russian("hello")
        assert result == "hello"

    def test_returns_empty_string_unchanged(self):
        from helpers.translation_helper import translate_to_russian
        assert translate_to_russian("") == ""

    def test_splits_long_text_into_chunks(self):
        from helpers.translation_helper import _split
        long = "A" * 400 + "\n\n" + "B" * 400
        chunks = _split(long)
        assert len(chunks) == 2
        assert all(len(c) <= 500 for c in chunks)

    def test_translation_helper_implements_abstract_helper(self):
        from helpers.translation_helper import TranslationHelper
        from helpers.abstract_helper import AbstractHelper
        assert issubclass(TranslationHelper, AbstractHelper)
        assert callable(TranslationHelper().process_text)


class TestWindguruCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from commands.windguru_command import WindguruCommand
        from datetime import datetime, timezone
        spots = [{"id": 137635, "name": "Lithuania - Svencele", "tz_offset": 0}]
        now = datetime.now(timezone.utc)
        init = now.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%d %H:%M:%S")
        mock_data = {"fcst": {
            "initdate": init,
            "hours": [8, 12, 16],
            "WINDSPD": [10.0, 15.0, 20.0],
            "GUST": [13.0, 19.0, 26.0],
            "WINDDIR": [220, 225, 200],
        }}
        with patch("commands.windguru_command._load_spots", return_value=spots), \
             patch("commands.windguru_command._fetch", return_value=mock_data):
            result = await WindguruCommand().run()
        assert "Lithuania - Svencele" in result
        assert "kn" in result
        assert "Сегодня" in result

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.windguru_command import WindguruCommand
        spots = [{"id": 137635, "name": "Lithuania - Svencele"}]
        with patch("commands.windguru_command._load_spots", return_value=spots), \
             patch("commands.windguru_command._fetch", return_value=None):
            result = await WindguruCommand().run()
        assert "Lithuania - Svencele" in result
        assert "прогноз" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_message_when_no_spots_configured(self):
        from commands.windguru_command import WindguruCommand
        with patch("commands.windguru_command._load_spots", return_value=[]):
            result = await WindguruCommand().run()
        assert "config.json" in result

    def test_has_required_interface(self):
        from commands.windguru_command import WindguruCommand
        from api.abstract_request_command import AbstractRequestCommand
        from api.abstract_cron_command import AbstractCronCommand
        assert issubclass(WindguruCommand, AbstractRequestCommand)
        assert issubclass(WindguruCommand, AbstractCronCommand)
        assert isinstance(WindguruCommand.NAME, str)
        assert isinstance(WindguruCommand.LABEL, str)
        assert callable(WindguruCommand().run)

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


class TestInstagramCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from commands.instagram_command import InstagramCommand
        post = {"shortcode": "abc123", "caption": "Hello", "is_video": False, "image": b"img", "url": "https://www.instagram.com/p/abc123/"}
        accounts = [{"username": "testuser", "name": "Test"}]
        with patch("commands.instagram_command._load_accounts", return_value=accounts), \
             patch("commands.instagram_command._fetch", return_value=post), \
             patch("commands.instagram_command._save_state"), \
             patch("commands.instagram_command._format", return_value={"text": "formatted", "photos": [b"img"]}):
            result = await InstagramCommand().run()
        assert result == {"text": "formatted", "photos": [b"img"]}

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.instagram_command import InstagramCommand
        accounts = [{"username": "testuser", "name": "Test"}]
        with patch("commands.instagram_command._load_accounts", return_value=accounts), \
             patch("commands.instagram_command._fetch", return_value=None):
            result = await InstagramCommand().run()
        assert "Could not fetch" in result

    @pytest.mark.asyncio
    async def test_returns_message_when_no_accounts(self):
        from commands.instagram_command import InstagramCommand
        with patch("commands.instagram_command._load_accounts", return_value=[]):
            result = await InstagramCommand().run()
        assert "config.json" in result

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_same(self):
        from commands.instagram_command import InstagramCommand
        post = {"shortcode": "abc123", "caption": "Hello", "is_video": False, "image": b"img", "url": "https://www.instagram.com/p/abc123/"}
        accounts = [{"username": "testuser", "name": "Test"}]
        with patch("commands.instagram_command._load_accounts", return_value=accounts), \
             patch("commands.instagram_command._fetch", return_value=post), \
             patch("commands.instagram_command._load_state", return_value={"testuser": "abc123"}):
            result = await InstagramCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_when_new(self):
        from commands.instagram_command import InstagramCommand
        post = {"shortcode": "new999", "caption": "New post", "is_video": False, "image": b"img", "url": "https://www.instagram.com/p/new999/"}
        accounts = [{"username": "testuser", "name": "Test"}]
        with patch("commands.instagram_command._load_accounts", return_value=accounts), \
             patch("commands.instagram_command._fetch", return_value=post), \
             patch("commands.instagram_command._load_state", return_value={"testuser": "old123"}), \
             patch("commands.instagram_command._save_state"), \
             patch("commands.instagram_command._format", return_value={"text": "new post", "photos": [b"img"]}):
            result = await InstagramCommand().run_if_new()
        assert result == {"text": "new post", "photos": [b"img"]}

    def test_has_required_interface(self):
        from commands.instagram_command import InstagramCommand
        from api.abstract_request_command import AbstractRequestCommand
        from api.abstract_news_command import AbstractNewsCommand
        assert issubclass(InstagramCommand, AbstractRequestCommand)
        assert issubclass(InstagramCommand, AbstractNewsCommand)
        assert isinstance(InstagramCommand.NAME, str)
        assert isinstance(InstagramCommand.LABEL, str)
        assert callable(InstagramCommand().run)
        assert callable(InstagramCommand().run_if_new)

    def test_format_returns_photos_for_image_post(self):
        from commands.instagram_command import _format
        post = {"is_video": False, "image": b"img", "caption": "hello", "url": "https://www.instagram.com/p/abc/"}
        with patch("commands.instagram_command.translate_to_russian", return_value="привет"):
            result = _format(post, {"username": "user", "name": "User"})
        assert result.get("photos") == [b"img"]
        assert "video" not in result

    def test_format_returns_video_for_video_post(self):
        from commands.instagram_command import _format
        post = {"is_video": True, "image": b"vid", "caption": "hello", "url": "https://www.instagram.com/p/abc/"}
        with patch("commands.instagram_command.translate_to_russian", return_value="привет"):
            result = _format(post, {"username": "user", "name": "User"})
        assert result.get("video") == b"vid"
        assert "photos" not in result

    def test_format_returns_text_only_when_no_image(self):
        from commands.instagram_command import _format
        post = {"is_video": False, "image": None, "caption": "hello", "url": "https://www.instagram.com/p/abc/"}
        with patch("commands.instagram_command.translate_to_russian", return_value="привет"):
            result = _format(post, {"username": "user", "name": "User"})
        assert "photos" not in result
        assert "text" in result


class TestIksurfmagCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from commands.iksurfmag_command import IksurfmagCommand
        data = {"url": "https://iksurfmag.com/news/1", "title": "Test", "text": "Body", "image": b"img"}
        with patch("commands.iksurfmag_command._fetch_latest", return_value=data), \
             patch("commands.iksurfmag_command._save_state"), \
             patch("commands.iksurfmag_command._format", return_value={"text": "formatted", "photos": [b"img"]}):
            result = await IksurfmagCommand().run()
        assert result == {"text": "formatted", "photos": [b"img"]}

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from commands.iksurfmag_command import IksurfmagCommand
        with patch("commands.iksurfmag_command._fetch_latest", return_value=None):
            result = await IksurfmagCommand().run()
        assert "Could not fetch" in result

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_same(self):
        from commands.iksurfmag_command import IksurfmagCommand
        data = {"url": "https://iksurfmag.com/news/1", "title": "T", "text": "B", "image": None}
        with patch("commands.iksurfmag_command._fetch_latest", return_value=data), \
             patch("commands.iksurfmag_command._load_state", return_value="https://iksurfmag.com/news/1"):
            result = await IksurfmagCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_when_new(self):
        from commands.iksurfmag_command import IksurfmagCommand
        data = {"url": "https://iksurfmag.com/news/2", "title": "T", "text": "B", "image": None}
        with patch("commands.iksurfmag_command._fetch_latest", return_value=data), \
             patch("commands.iksurfmag_command._load_state", return_value="https://iksurfmag.com/news/1"), \
             patch("commands.iksurfmag_command._save_state"), \
             patch("commands.iksurfmag_command._format", return_value={"text": "new article"}):
            result = await IksurfmagCommand().run_if_new()
        assert result == {"text": "new article"}

    def test_has_required_interface(self):
        from commands.iksurfmag_command import IksurfmagCommand
        from api.abstract_request_command import AbstractRequestCommand
        from api.abstract_news_command import AbstractNewsCommand
        assert issubclass(IksurfmagCommand, AbstractRequestCommand)
        assert issubclass(IksurfmagCommand, AbstractNewsCommand)
        assert isinstance(IksurfmagCommand.NAME, str)
        assert isinstance(IksurfmagCommand.LABEL, str)
        assert callable(IksurfmagCommand().run)
        assert callable(IksurfmagCommand().run_if_new)

    def test_format_returns_photos_when_image_present(self):
        from commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body", "image": b"img"}
        with patch("commands.iksurfmag_command.rewrite_to_russian", return_value="текст"):
            result = _format(data)
        assert result.get("photos") == [b"img"]
        assert "Title" in result["text"]

    def test_format_returns_text_only_when_no_image(self):
        from commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body", "image": None}
        with patch("commands.iksurfmag_command.rewrite_to_russian", return_value="текст"):
            result = _format(data)
        assert "photos" not in result
        assert "text" in result

    def test_format_falls_back_to_translation_when_rewrite_fails(self):
        from commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body", "image": None}
        with patch("commands.iksurfmag_command.rewrite_to_russian", return_value=None), \
             patch("commands.iksurfmag_command.translate_to_russian", return_value="переведено"):
            result = _format(data)
        assert "переведено" in result["text"]


class TestRewriteHelper:
    def test_returns_rewritten_text(self):
        from helpers.rewrite_helper import rewrite_to_russian
        mock_response = {"choices": [{"message": {"content": "текст на русском"}}]}
        with patch("helpers.rewrite_helper.requests.post") as mock_post, \
             patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = lambda: None
            result = rewrite_to_russian("Title", "Article body")
        assert result == "текст на русском"

    def test_returns_none_when_no_api_key(self):
        from helpers.rewrite_helper import rewrite_to_russian
        import os
        env = {k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            result = rewrite_to_russian("Title", "Body")
        assert result is None

    def test_returns_none_on_api_error(self):
        from helpers.rewrite_helper import rewrite_to_russian
        with patch("helpers.rewrite_helper.requests.post", side_effect=Exception("error")), \
             patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
            result = rewrite_to_russian("Title", "Body")
        assert result is None
