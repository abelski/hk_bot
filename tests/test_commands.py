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
        with patch("commands.iksurfmag_command.rewrite_to_russian", return_value="текст"), \
             patch("commands.iksurfmag_command.translate_to_russian", return_value="Заголовок"):
            result = _format(data)
        assert result.get("photos") == [b"img"]
        assert "Заголовок" in result["text"]

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

    def test_format_falls_back_to_url_when_download_fails(self):
        from commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body",
                "image": None, "video_url": "https://www.youtube.com/watch?v=abc123"}
        with patch("commands.iksurfmag_command.rewrite_to_russian", return_value="текст"), \
             patch("commands.iksurfmag_command.download_youtube_video", return_value=None):
            result = _format(data)
        assert "https://www.youtube.com/watch?v=abc123" in result["text"]
        assert "photos" not in result
        assert "video" not in result

    def test_format_embeds_video_when_download_succeeds(self):
        from commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body",
                "image": None, "video_url": "https://www.youtube.com/watch?v=abc123"}
        with patch("commands.iksurfmag_command.rewrite_to_russian", return_value="текст"), \
             patch("commands.iksurfmag_command.download_youtube_video", return_value=b"videodata"):
            result = _format(data)
        assert result.get("video") == b"videodata"
        assert "abc123" not in result["text"]
        assert "photos" not in result

    def test_youtube_watch_url_converts_embed(self):
        from commands.iksurfmag_command import _youtube_watch_url
        result = _youtube_watch_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_watch_url_returns_none_for_non_embed(self):
        from commands.iksurfmag_command import _youtube_watch_url
        assert _youtube_watch_url("https://example.com/video.mp4") is None

    def test_fetch_article_data_extracts_text_and_video(self):
        from commands.iksurfmag_command import _fetch_article_data
        # Simulate iksurfmag structure: injected <body> inside .single-post,
        # classless <p> for article text, lazy-loaded YouTube iframe via data-src
        html = """
        <html><body>
          <div class="single-post">
            <!DOCTYPE html><html><body>
              <section class="promo"><p class="text-muted">Subscribe!</p></section>
              <p></p>
              <p>The winner of Lords Of Tram 2026 and this just shows why…</p>
              <iframe class="lazyload" data-src="https://www.youtube.com/embed/FGQpFpAYeik?rel=0"></iframe>
            </body></html>
          </div>
        </body></html>"""
        mock_resp = type("R", (), {"text": html, "raise_for_status": lambda _: None})()
        with patch("commands.iksurfmag_command.requests.get", return_value=mock_resp):
            result = _fetch_article_data("https://iksurfmag.com/news/1")
        assert "Lords Of Tram" in result["text"]
        assert result["video_url"] == "https://www.youtube.com/watch?v=FGQpFpAYeik"

    def test_fetch_article_data_returns_empty_on_failure(self):
        from commands.iksurfmag_command import _fetch_article_data
        with patch("commands.iksurfmag_command.requests.get", side_effect=Exception("err")):
            result = _fetch_article_data("https://iksurfmag.com/news/1")
        assert result == {"text": "", "video_url": None}

    def test_youtube_detected_from_ytimg_thumbnail_in_media(self):
        """When article page fetch fails, video should be detected from ytimg.com thumbnail URL."""
        import xml.etree.ElementTree as ET
        from commands.iksurfmag_command import _parse_item
        rss_xml = """<item>
            <title>Test</title>
            <link>https://iksurfmag.com/news/1</link>
            <ns0:content xmlns:ns0="http://search.yahoo.com/mrss/"
                url="https://i.ytimg.com/vi/FGQpFpAYeik/maxresdefault.jpg" medium="image"/>
        </item>"""
        item = ET.fromstring(rss_xml)
        with patch("commands.iksurfmag_command._fetch_article_data",
                   return_value={"text": "", "video_url": None}):
            result = _parse_item(item)
        assert result["video_url"] == "https://www.youtube.com/watch?v=FGQpFpAYeik"
        assert result["image"] is None

    def test_rss_fallback_strips_iksurfmag_boilerplate(self):
        """RSS text fallback should exclude 'first appeared on' and 'Read the full article' lines."""
        import xml.etree.ElementTree as ET
        from commands.iksurfmag_command import _parse_item
        rss_xml = """<item>
            <title>Test</title>
            <link>https://iksurfmag.com/news/1</link>
            <content:encoded xmlns:content="http://purl.org/rss/1.0/modules/content/"><![CDATA[
                <p>Great article text.</p>
                <p>The post Test first appeared on IKSURFMAG.</p>
                <p>Read the full article here: Test</p>
            ]]></content:encoded>
        </item>"""
        item = ET.fromstring(rss_xml)
        with patch("commands.iksurfmag_command._fetch_article_data",
                   return_value={"text": "", "video_url": None}):
            result = _parse_item(item)
        assert "Great article text" in result["text"]
        assert "IKSURFMAG" not in result["text"]
        assert "full article" not in result["text"].lower()


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


class TestYoutubeHelper:
    def _make_fake_ydl(self):
        from unittest.mock import MagicMock
        fake = MagicMock()
        fake.__enter__ = MagicMock(return_value=fake)
        fake.__exit__ = MagicMock(return_value=False)
        return fake

    def _mock_yt_dlp(self, fake_ydl):
        import sys
        from unittest.mock import MagicMock
        mock_module = MagicMock()
        mock_module.YoutubeDL.return_value = fake_ydl
        return patch.dict(sys.modules, {"yt_dlp": mock_module})

    def test_returns_video_bytes_on_success(self):
        from helpers.youtube_helper import download_youtube_video
        from unittest.mock import MagicMock, mock_open

        fake_ydl = self._make_fake_ydl()
        video_bytes = b"fakevideocontent"

        with self._mock_yt_dlp(fake_ydl), \
             patch("helpers.youtube_helper.tempfile.TemporaryDirectory") as mock_tmpdir, \
             patch("helpers.youtube_helper.os.listdir", return_value=["video.mp4"]), \
             patch("builtins.open", mock_open(read_data=video_bytes)), \
             patch("helpers.youtube_helper.os.path.join", side_effect=os.path.join):
            mock_tmpdir.return_value.__enter__ = MagicMock(return_value="/tmp/fake")
            mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)
            result = download_youtube_video("https://www.youtube.com/watch?v=abc123")
        assert result == video_bytes

    def test_returns_none_on_download_error(self):
        from helpers.youtube_helper import download_youtube_video

        fake_ydl = self._make_fake_ydl()
        fake_ydl.download.side_effect = Exception("download failed")

        with self._mock_yt_dlp(fake_ydl):
            result = download_youtube_video("https://www.youtube.com/watch?v=abc123")
        assert result is None

    def test_returns_none_when_no_files_downloaded(self):
        from helpers.youtube_helper import download_youtube_video
        from unittest.mock import MagicMock

        fake_ydl = self._make_fake_ydl()

        with self._mock_yt_dlp(fake_ydl), \
             patch("helpers.youtube_helper.tempfile.TemporaryDirectory") as mock_tmpdir, \
             patch("helpers.youtube_helper.os.listdir", return_value=[]):
            mock_tmpdir.return_value.__enter__ = MagicMock(return_value="/tmp/fake")
            mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)
            result = download_youtube_video("https://www.youtube.com/watch?v=abc123")
        assert result is None

    def test_returns_none_when_yt_dlp_not_installed(self):
        import sys
        from helpers.youtube_helper import download_youtube_video

        with patch.dict(sys.modules, {"yt_dlp": None}):
            result = download_youtube_video("https://www.youtube.com/watch?v=abc123")
        assert result is None


class TestYoutubeCommand:
    @pytest.mark.asyncio
    async def test_run_returns_formatted_result(self):
        from commands.youtube_command import YoutubeCommand
        video_data = {
            "url": "https://www.youtube.com/watch?v=abc123",
            "title": "Test Video",
            "description": "Test description",
            "channel": "TestChannel",
        }
        formatted = {"text": "*Test Video*\n\nRussian text", "video": b"videodata"}
        with patch("commands.youtube_command.load_config", return_value={"youtube_channels": ["https://www.youtube.com/@test"]}), \
             patch("commands.youtube_command._fetch_latest_video", return_value=video_data), \
             patch("commands.youtube_command._save_state"), \
             patch("commands.youtube_command._format", return_value=formatted):
            result = await YoutubeCommand().run()
        assert result == formatted

    @pytest.mark.asyncio
    async def test_run_returns_error_when_all_channels_fail(self):
        from commands.youtube_command import YoutubeCommand
        with patch("commands.youtube_command.load_config", return_value={"youtube_channels": ["https://www.youtube.com/@test"]}), \
             patch("commands.youtube_command._fetch_latest_video", return_value=None):
            result = await YoutubeCommand().run()
        assert "Could not fetch" in result

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_no_new_videos(self):
        from commands.youtube_command import YoutubeCommand
        video_data = {"url": "https://www.youtube.com/watch?v=abc123", "title": "T", "description": "", "channel": "C"}
        state = {"https://www.youtube.com/@test": "https://www.youtube.com/watch?v=abc123"}
        with patch("commands.youtube_command.load_config", return_value={"youtube_channels": ["https://www.youtube.com/@test"]}), \
             patch("commands.youtube_command._fetch_latest_video", return_value=video_data), \
             patch("commands.youtube_command._load_state", return_value=state):
            result = await YoutubeCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_for_new_video(self):
        from commands.youtube_command import YoutubeCommand
        video_data = {"url": "https://www.youtube.com/watch?v=newvideo", "title": "New", "description": "", "channel": "C"}
        state = {"https://www.youtube.com/@test": "https://www.youtube.com/watch?v=oldvideo"}
        formatted = {"text": "*New*\n\nRussian", "video": b"bytes"}
        with patch("commands.youtube_command.load_config", return_value={"youtube_channels": ["https://www.youtube.com/@test"]}), \
             patch("commands.youtube_command._fetch_latest_video", return_value=video_data), \
             patch("commands.youtube_command._load_state", return_value=state), \
             patch("commands.youtube_command._save_state"), \
             patch("commands.youtube_command._format", return_value=formatted):
            result = await YoutubeCommand().run_if_new()
        assert result == formatted

    def test_has_required_interface(self):
        from commands.youtube_command import YoutubeCommand
        from api.abstract_request_command import AbstractRequestCommand
        from api.abstract_news_command import AbstractNewsCommand
        assert issubclass(YoutubeCommand, AbstractRequestCommand)
        assert issubclass(YoutubeCommand, AbstractNewsCommand)
        assert YoutubeCommand.NAME == "youtube"
        assert isinstance(YoutubeCommand.LABEL, str)
