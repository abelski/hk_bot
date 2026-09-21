"""
Unit tests for command classes in src/news/commands/.
"""

import os
import pytest
from unittest.mock import patch


class TestWooCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_leaderboard(self):
        from src.news.commands.woo_command import WooCommand
        entries = [{"rank": 1, "user": {"first_name": "A", "last_name": "B"}, "score": 10}]
        with patch("src.news.commands.woo_command._fetch_entries", return_value=entries), \
             patch("src.news.commands.woo_command._format_leaderboard", return_value="formatted"):
            result = await WooCommand().run()
        assert result == "formatted"

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from src.news.commands.woo_command import WooCommand
        with patch("src.news.commands.woo_command._fetch_entries", return_value=None):
            result = await WooCommand().run()
        assert "Could not fetch" in result

    def test_has_required_interface(self):
        from src.news.commands.woo_command import WooCommand
        from src.news.api.abstract_request_command import AbstractRequestCommand
        from src.news.api.abstract_cron_command import AbstractCronCommand
        assert issubclass(WooCommand, AbstractRequestCommand)
        assert issubclass(WooCommand, AbstractCronCommand)
        assert isinstance(WooCommand.NAME, str)
        assert isinstance(WooCommand.LABEL, str)
        assert callable(WooCommand().run)

    def test_format_leaderboard_with_yesterday_and_alltime(self):
        from src.news.commands.woo_command import _format_leaderboard
        entry = {"rank": 1, "score": 25.9, "user": {"first_name": "Raigo", "last_name": "Test"}}
        alltime = {"rank": 1, "score": 30.0, "user": {"first_name": "Kaimar", "last_name": "H"}}
        countries = [{"name": "Estonia", "code": "EE"}]
        country_data = {"EE": {"today": entry, "alltime": alltime}}
        result = _format_leaderboard([entry], top_n=1, countries=countries, country_data=country_data)
        assert "🇪🇪 Estonia" in result
        assert "сегодня - Raigo Test · 25.9m" in result
        assert "рекорд - Kaimar H · 30.0m" in result

    def test_format_leaderboard_no_today(self):
        from src.news.commands.woo_command import _format_leaderboard
        entry = {"rank": 1, "score": 25.9, "user": {"first_name": "Raigo", "last_name": "Test"}}
        alltime = {"rank": 1, "score": 30.0, "user": {"first_name": "Kaimar", "last_name": "H"}}
        countries = [{"name": "Estonia", "code": "EE"}]
        country_data = {"EE": {"today": None, "alltime": alltime}}
        result = _format_leaderboard([entry], top_n=1, countries=countries, country_data=country_data)
        assert "сегодня - нет" in result
        assert "рекорд - Kaimar H · 30.0m" in result

    def test_format_leaderboard_no_countries(self):
        from src.news.commands.woo_command import _format_leaderboard
        entries = [{"rank": 1, "score": 10.0, "user": {"first_name": "A", "last_name": "B"}}]
        result = _format_leaderboard(entries, top_n=3, countries=[], country_data={})
        assert "рекорд" not in result
        assert "вчера" not in result

    def test_flag_from_code(self):
        from src.news.commands.woo_command import _flag_from_code
        assert _flag_from_code("RU") == "🇷🇺"
        assert _flag_from_code("BY") == "🇧🇾"
        assert _flag_from_code("EE") == "🇪🇪"


class TestSurfrCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_leaderboard(self):
        from src.news.commands.surfr_command import SurfrCommand
        entries = [{"user": {"name": "Denis K", "country": "NL"}, "value": 36.3}]
        with patch("src.news.commands.surfr_command._fetch_leaderboard", return_value=entries), \
             patch("src.news.commands.surfr_command._format_leaderboard", return_value="formatted"):
            result = await SurfrCommand().run()
        assert result == "formatted"

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from src.news.commands.surfr_command import SurfrCommand
        with patch("src.news.commands.surfr_command._fetch_leaderboard", return_value=None):
            result = await SurfrCommand().run()
        assert "Could not fetch" in result

    def test_has_required_interface(self):
        from src.news.commands.surfr_command import SurfrCommand
        from src.news.api.abstract_request_command import AbstractRequestCommand
        assert issubclass(SurfrCommand, AbstractRequestCommand)
        assert isinstance(SurfrCommand.NAME, str)
        assert isinstance(SurfrCommand.LABEL, str)
        assert callable(SurfrCommand().run)

    def test_format_leaderboard_shows_top5_with_flags(self):
        from src.news.commands.surfr_command import _format_leaderboard
        entries = [
            {"user": {"name": "J. Overbeek", "country": "NL"}, "value": 36.3},
            {"user": {"name": "Hugo W", "country": "NZ"}, "value": 36.27},
            {"user": {"name": "Ivan", "country": "RU"}, "value": 17.5},
        ]
        result = _format_leaderboard(entries)
        assert "#1 · 🇳🇱 J. Overbeek · 36.3m" in result
        assert "#2 · 🇳🇿 Hugo W · 36.27m" in result
        assert "#3 · 🇷🇺 Ivan · 17.5m" in result

    def test_format_leaderboard_empty(self):
        from src.news.commands.surfr_command import _format_leaderboard
        result = _format_leaderboard([])
        assert "Результатов пока нет" in result

    def test_format_leaderboard_no_country(self):
        from src.news.commands.surfr_command import _format_leaderboard
        entries = [{"user": {"name": "Unknown Rider"}, "value": 10.0}]
        result = _format_leaderboard(entries)
        assert "#1 · Unknown Rider · 10.0m" in result

    def test_rider_name_reads_nested_user(self):
        from src.news.commands.surfr_command import _rider_name
        assert _rider_name({"user": {"name": "Denis K"}}) == "Denis K"
        assert _rider_name({"user": {}}) == "Unknown"
        assert _rider_name({}) == "Unknown"

    def test_rider_score_rounds_float(self):
        from src.news.commands.surfr_command import _rider_score
        assert _rider_score({"value": 36.271234}) == 36.27
        assert _rider_score({}) == 0

    def test_flag_from_code(self):
        from src.news.commands.surfr_command import _flag_from_code
        assert _flag_from_code("NL") == "🇳🇱"
        assert _flag_from_code("RU") == "🇷🇺"
        assert _flag_from_code("") == ""


class TestHkrCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from src.news.commands.hkr_command import HkrCommand
        review = {"id": 1, "productName": "Test Kite", "brand": "Brand", "productType": "Kite",
                  "writeUp": "Great kite.", "safetyStatus": "safe",
                  "user": {"firstName": "A", "lastName": "B"}, "images": []}
        with patch("src.news.commands.hkr_command._fetch", return_value=review), \
             patch("src.news.commands.hkr_command._save_state"), \
             patch("src.news.commands.hkr_command._format", return_value={"text": "formatted", "photos": []}):
            result = await HkrCommand().run()
        assert result == {"text": "formatted", "photos": []}

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from src.news.commands.hkr_command import HkrCommand
        with patch("src.news.commands.hkr_command._fetch", return_value=None):
            result = await HkrCommand().run()
        assert "Could not fetch" in result

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_same(self):
        from src.news.commands.hkr_command import HkrCommand
        review = {"id": 42, "productName": "X", "brand": "B", "productType": "T",
                  "writeUp": ".", "safetyStatus": "safe",
                  "user": {"firstName": "X", "lastName": "Y"}, "images": []}
        with patch("src.news.commands.hkr_command._fetch", return_value=review), \
             patch("src.news.commands.hkr_command._load_state", return_value=42):
            result = await HkrCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_when_new(self):
        from src.news.commands.hkr_command import HkrCommand
        review = {"id": 99, "productName": "X", "brand": "B", "productType": "T",
                  "writeUp": ".", "safetyStatus": "safe",
                  "user": {"firstName": "X", "lastName": "Y"}, "images": []}
        with patch("src.news.commands.hkr_command._fetch", return_value=review), \
             patch("src.news.commands.hkr_command._load_state", return_value=1), \
             patch("src.news.commands.hkr_command._save_state"), \
             patch("src.news.commands.hkr_command._format", return_value={"text": "new review", "photos": []}):
            result = await HkrCommand().run_if_new()
        assert result == {"text": "new review", "photos": []}

    def test_has_required_interface(self):
        from src.news.commands.hkr_command import HkrCommand
        from src.news.api.abstract_request_command import AbstractRequestCommand
        from src.news.api.abstract_news_command import AbstractNewsCommand
        assert issubclass(HkrCommand, AbstractRequestCommand)
        assert issubclass(HkrCommand, AbstractNewsCommand)
        assert isinstance(HkrCommand.NAME, str)
        assert isinstance(HkrCommand.LABEL, str)
        assert callable(HkrCommand().run)
        assert callable(HkrCommand().run_if_new)


class TestTranslateHelper:
    def test_returns_translated_text(self):
        from src.news.helpers.translation_helper import translate_to_russian
        with patch("src.news.helpers.translation_helper._translate_chunk", return_value="привет"):
            result = translate_to_russian("hello")
        assert result == "привет"

    def test_falls_back_on_chunk_failure(self):
        from src.news.helpers.translation_helper import translate_to_russian
        with patch("src.news.helpers.translation_helper._translate_chunk", return_value=None):
            result = translate_to_russian("hello")
        assert result == "hello"

    def test_returns_empty_string_unchanged(self):
        from src.news.helpers.translation_helper import translate_to_russian
        assert translate_to_russian("") == ""

    def test_splits_long_text_into_chunks(self):
        from src.news.helpers.translation_helper import _split
        long = "A" * 400 + "\n\n" + "B" * 400
        chunks = _split(long)
        assert len(chunks) == 2
        assert all(len(c) <= 500 for c in chunks)

    def test_translation_helper_implements_abstract_helper(self):
        from src.news.helpers.translation_helper import TranslationHelper
        from src.news.helpers.abstract_helper import AbstractHelper
        assert issubclass(TranslationHelper, AbstractHelper)
        assert callable(TranslationHelper().process_text)


class TestWindguruCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from src.news.commands.windguru_command import WindguruCommand
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
        with patch("src.news.commands.windguru_command._load_spots", return_value=spots), \
             patch("src.news.commands.windguru_command._fetch", return_value=mock_data):
            result = await WindguruCommand().run()
        assert "Lithuania - Svencele" in result
        assert "kn" in result
        assert "Сегодня" in result

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from src.news.commands.windguru_command import WindguruCommand
        spots = [{"id": 137635, "name": "Lithuania - Svencele"}]
        with patch("src.news.commands.windguru_command._load_spots", return_value=spots), \
             patch("src.news.commands.windguru_command._fetch", return_value=None):
            result = await WindguruCommand().run()
        assert "Lithuania - Svencele" in result
        assert "прогноз" in result.lower()

    @pytest.mark.asyncio
    async def test_returns_message_when_no_spots_configured(self):
        from src.news.commands.windguru_command import WindguruCommand
        with patch("src.news.commands.windguru_command._load_spots", return_value=[]):
            result = await WindguruCommand().run()
        assert "config.json" in result

    def test_has_required_interface(self):
        from src.news.commands.windguru_command import WindguruCommand
        from src.news.api.abstract_request_command import AbstractRequestCommand
        from src.news.api.abstract_cron_command import AbstractCronCommand
        assert issubclass(WindguruCommand, AbstractRequestCommand)
        assert issubclass(WindguruCommand, AbstractCronCommand)
        assert isinstance(WindguruCommand.NAME, str)
        assert isinstance(WindguruCommand.LABEL, str)
        assert callable(WindguruCommand().run)

    def test_deg_to_dir(self):
        from src.news.commands.windguru_command import _deg_to_dir
        assert _deg_to_dir(0) == "N"
        assert _deg_to_dir(180) == "S"
        assert _deg_to_dir(225) == "SW"

    def test_wind_color(self):
        from src.news.commands.windguru_command import _wind_color
        assert _wind_color(5) == "⚪"
        assert _wind_color(10) == "🔵"
        assert _wind_color(16) == "🟢"
        assert _wind_color(24) == "🟡"
        assert _wind_color(35) == "🔴"

    def test_wind_stars(self):
        from src.news.commands.windguru_command import _wind_stars
        assert _wind_stars(5) == "·"
        assert _wind_stars(10) == "⭐"
        assert _wind_stars(15) == "⭐⭐⭐"
        assert _wind_stars(20) == "⭐⭐⭐⭐⭐"
        assert _wind_stars(28) == "⭐⭐⭐"
        assert _wind_stars(35) == "⭐"


class TestIksurfmagCommand:
    @pytest.mark.asyncio
    async def test_returns_formatted_result(self):
        from src.news.commands.iksurfmag_command import IksurfmagCommand
        data = {"url": "https://iksurfmag.com/news/1", "title": "Test", "text": "Body", "image": b"img"}
        with patch("src.news.commands.iksurfmag_command._fetch_latest", return_value=data), \
             patch("src.news.commands.iksurfmag_command._save_state"), \
             patch("src.news.commands.iksurfmag_command._format", return_value={"text": "formatted", "photos": [b"img"]}):
            result = await IksurfmagCommand().run()
        assert result == {"text": "formatted", "photos": [b"img"]}

    @pytest.mark.asyncio
    async def test_returns_error_when_fetch_fails(self):
        from src.news.commands.iksurfmag_command import IksurfmagCommand
        with patch("src.news.commands.iksurfmag_command._fetch_latest", return_value=None):
            result = await IksurfmagCommand().run()
        assert "Could not fetch" in result

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_same(self):
        from src.news.commands.iksurfmag_command import IksurfmagCommand
        data = {"url": "https://iksurfmag.com/news/1", "title": "T", "text": "B", "image": None}
        with patch("src.news.commands.iksurfmag_command._fetch_latest", return_value=data), \
             patch("src.news.commands.iksurfmag_command._load_state", return_value="https://iksurfmag.com/news/1"):
            result = await IksurfmagCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_when_new(self):
        from src.news.commands.iksurfmag_command import IksurfmagCommand
        data = {"url": "https://iksurfmag.com/news/2", "title": "T", "text": "B", "image": None}
        with patch("src.news.commands.iksurfmag_command._fetch_latest", return_value=data), \
             patch("src.news.commands.iksurfmag_command._load_state", return_value="https://iksurfmag.com/news/1"), \
             patch("src.news.commands.iksurfmag_command._save_state"), \
             patch("src.news.commands.iksurfmag_command._format", return_value={"text": "new article"}):
            result = await IksurfmagCommand().run_if_new()
        assert result == {"text": "new article"}

    def test_has_required_interface(self):
        from src.news.commands.iksurfmag_command import IksurfmagCommand
        from src.news.api.abstract_request_command import AbstractRequestCommand
        from src.news.api.abstract_news_command import AbstractNewsCommand
        assert issubclass(IksurfmagCommand, AbstractRequestCommand)
        assert issubclass(IksurfmagCommand, AbstractNewsCommand)
        assert isinstance(IksurfmagCommand.NAME, str)
        assert isinstance(IksurfmagCommand.LABEL, str)
        assert callable(IksurfmagCommand().run)
        assert callable(IksurfmagCommand().run_if_new)

    def test_format_returns_photos_when_image_present(self):
        from src.news.commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body", "image": b"img"}
        with patch("src.news.commands.iksurfmag_command.rewrite_to_russian", return_value="текст"), \
             patch("src.news.commands.iksurfmag_command.translate_to_russian", return_value="Заголовок"):
            result = _format(data)
        assert result.get("photos") == [b"img"]
        assert "Заголовок" in result["text"]

    def test_format_returns_text_only_when_no_image(self):
        from src.news.commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body", "image": None}
        with patch("src.news.commands.iksurfmag_command.rewrite_to_russian", return_value="текст"):
            result = _format(data)
        assert "photos" not in result
        assert "text" in result

    def test_format_falls_back_to_translation_when_rewrite_fails(self):
        from src.news.commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body", "image": None}
        with patch("src.news.commands.iksurfmag_command.rewrite_to_russian", return_value=None), \
             patch("src.news.commands.iksurfmag_command.translate_to_russian", return_value="переведено"):
            result = _format(data)
        assert "переведено" in result["text"]

    def test_format_drops_body_when_translation_fails(self):
        from src.news.commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "English Title",
                "text": "English body", "image": None}
        with patch("src.news.commands.iksurfmag_command.rewrite_to_russian", return_value=None), \
             patch("src.news.commands.iksurfmag_command.translate_to_russian", side_effect=lambda t: t):
            result = _format(data)
        assert "English body" not in result["text"]
        assert result["text"].count("English Title") == 1

    def test_format_falls_back_to_url_when_download_fails(self):
        from src.news.commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body",
                "image": None, "video_url": "https://www.youtube.com/watch?v=abc123"}
        with patch("src.news.commands.iksurfmag_command.rewrite_to_russian", return_value="текст"), \
             patch("src.news.commands.iksurfmag_command.download_youtube_video", return_value=None):
            result = _format(data)
        assert "https://www.youtube.com/watch?v=abc123" in result["text"]
        assert "photos" not in result
        assert "video" not in result

    def test_format_embeds_video_when_download_succeeds(self):
        from src.news.commands.iksurfmag_command import _format
        data = {"url": "https://iksurfmag.com/news/1", "title": "Title", "text": "Body",
                "image": None, "video_url": "https://www.youtube.com/watch?v=abc123"}
        with patch("src.news.commands.iksurfmag_command.rewrite_to_russian", return_value="текст"), \
             patch("src.news.commands.iksurfmag_command.download_youtube_video", return_value=b"videodata"):
            result = _format(data)
        assert result.get("video") == b"videodata"
        assert "abc123" not in result["text"]
        assert "photos" not in result

    def test_youtube_watch_url_converts_embed(self):
        from src.news.commands.iksurfmag_command import _youtube_watch_url
        result = _youtube_watch_url("https://www.youtube.com/embed/dQw4w9WgXcQ")
        assert result == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    def test_youtube_watch_url_returns_none_for_non_embed(self):
        from src.news.commands.iksurfmag_command import _youtube_watch_url
        assert _youtube_watch_url("https://example.com/video.mp4") is None

    def test_fetch_article_data_extracts_text_and_video(self):
        from src.news.commands.iksurfmag_command import _fetch_article_data
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
        with patch("src.news.commands.iksurfmag_command.requests.get", return_value=mock_resp):
            result = _fetch_article_data("https://iksurfmag.com/news/1")
        assert "Lords Of Tram" in result["text"]
        assert result["video_url"] == "https://www.youtube.com/watch?v=FGQpFpAYeik"

    def test_fetch_article_data_returns_empty_on_failure(self):
        from src.news.commands.iksurfmag_command import _fetch_article_data
        with patch("src.news.commands.iksurfmag_command.requests.get", side_effect=Exception("err")):
            result = _fetch_article_data("https://iksurfmag.com/news/1")
        assert result == {"text": "", "video_url": None}

    def test_youtube_detected_from_ytimg_thumbnail_in_media(self):
        """When article page fetch fails, video should be detected from ytimg.com thumbnail URL."""
        import xml.etree.ElementTree as ET
        from src.news.commands.iksurfmag_command import _parse_item
        rss_xml = """<item>
            <title>Test</title>
            <link>https://iksurfmag.com/news/1</link>
            <ns0:content xmlns:ns0="http://search.yahoo.com/mrss/"
                url="https://i.ytimg.com/vi/FGQpFpAYeik/maxresdefault.jpg" medium="image"/>
        </item>"""
        item = ET.fromstring(rss_xml)
        with patch("src.news.commands.iksurfmag_command._fetch_article_data",
                   return_value={"text": "", "video_url": None}):
            result = _parse_item(item)
        assert result["video_url"] == "https://www.youtube.com/watch?v=FGQpFpAYeik"
        assert result["image"] is None

    def test_rss_fallback_strips_iksurfmag_boilerplate(self):
        """RSS text fallback should exclude 'first appeared on' and 'Read the full article' lines."""
        import xml.etree.ElementTree as ET
        from src.news.commands.iksurfmag_command import _parse_item
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
        with patch("src.news.commands.iksurfmag_command._fetch_article_data",
                   return_value={"text": "", "video_url": None}):
            result = _parse_item(item)
        assert "Great article text" in result["text"]
        assert "IKSURFMAG" not in result["text"]
        assert "full article" not in result["text"].lower()


class TestRewriteHelper:
    def test_returns_rewritten_text(self):
        from src.news.helpers.rewrite_helper import rewrite_to_russian
        mock_response = {"choices": [{"message": {"content": "текст на русском"}}]}
        with patch("src.news.helpers.rewrite_helper.requests.post") as mock_post, \
             patch.dict("os.environ", {"GROQ_API_KEY": "test-key"}):
            mock_post.return_value.json.return_value = mock_response
            mock_post.return_value.raise_for_status = lambda: None
            result = rewrite_to_russian("Title", "Article body")
        assert result == "текст на русском"

    def test_returns_none_when_no_api_key(self):
        from src.news.helpers.rewrite_helper import rewrite_to_russian
        import os
        env = {k: v for k, v in os.environ.items() if k != "GROQ_API_KEY"}
        with patch.dict("os.environ", env, clear=True):
            result = rewrite_to_russian("Title", "Body")
        assert result is None

    def test_returns_none_on_api_error(self):
        from src.news.helpers.rewrite_helper import rewrite_to_russian
        with patch("src.news.helpers.rewrite_helper.requests.post", side_effect=Exception("error")), \
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
        from src.news.helpers.youtube_helper import download_youtube_video
        from unittest.mock import MagicMock, mock_open

        fake_ydl = self._make_fake_ydl()
        video_bytes = b"fakevideocontent"

        with self._mock_yt_dlp(fake_ydl), \
             patch("src.news.helpers.youtube_helper.tempfile.TemporaryDirectory") as mock_tmpdir, \
             patch("src.news.helpers.youtube_helper.os.listdir", return_value=["video.mp4"]), \
             patch("builtins.open", mock_open(read_data=video_bytes)), \
             patch("src.news.helpers.youtube_helper.os.path.join", side_effect=os.path.join):
            mock_tmpdir.return_value.__enter__ = MagicMock(return_value="/tmp/fake")
            mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)
            result = download_youtube_video("https://www.youtube.com/watch?v=abc123")
        assert result == video_bytes

    def test_returns_none_on_download_error(self):
        from src.news.helpers.youtube_helper import download_youtube_video

        fake_ydl = self._make_fake_ydl()
        fake_ydl.download.side_effect = Exception("download failed")

        with self._mock_yt_dlp(fake_ydl):
            result = download_youtube_video("https://www.youtube.com/watch?v=abc123")
        assert result is None

    def test_returns_none_when_no_files_downloaded(self):
        from src.news.helpers.youtube_helper import download_youtube_video
        from unittest.mock import MagicMock

        fake_ydl = self._make_fake_ydl()

        with self._mock_yt_dlp(fake_ydl), \
             patch("src.news.helpers.youtube_helper.tempfile.TemporaryDirectory") as mock_tmpdir, \
             patch("src.news.helpers.youtube_helper.os.listdir", return_value=[]):
            mock_tmpdir.return_value.__enter__ = MagicMock(return_value="/tmp/fake")
            mock_tmpdir.return_value.__exit__ = MagicMock(return_value=False)
            result = download_youtube_video("https://www.youtube.com/watch?v=abc123")
        assert result is None

    def test_returns_none_when_yt_dlp_not_installed(self):
        import sys
        from src.news.helpers.youtube_helper import download_youtube_video

        with patch.dict(sys.modules, {"yt_dlp": None}):
            result = download_youtube_video("https://www.youtube.com/watch?v=abc123")
        assert result is None


class TestYoutubeCommand:
    @pytest.mark.asyncio
    async def test_run_returns_formatted_result(self):
        from src.news.commands.youtube_command import YoutubeCommand
        video_data = {
            "url": "https://www.youtube.com/watch?v=abc123",
            "title": "Test Video",
            "description": "Test description",
            "channel": "TestChannel",
        }
        formatted = {"text": "*Test Video*\n\nRussian text", "video": b"videodata"}
        with patch("src.news.commands.youtube_command.load_config", return_value={"youtube_channels": ["https://www.youtube.com/@test"]}), \
             patch("src.news.commands.youtube_command._fetch_latest_video", return_value=video_data), \
             patch("src.news.commands.youtube_command._save_state"), \
             patch("src.news.commands.youtube_command._format", return_value=formatted):
            result = await YoutubeCommand().run()
        assert result == formatted

    @pytest.mark.asyncio
    async def test_run_returns_error_when_all_channels_fail(self):
        from src.news.commands.youtube_command import YoutubeCommand
        with patch("src.news.commands.youtube_command.load_config", return_value={"youtube_channels": ["https://www.youtube.com/@test"]}), \
             patch("src.news.commands.youtube_command._fetch_latest_video", return_value=None):
            result = await YoutubeCommand().run()
        assert "Could not fetch" in result

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_no_new_videos(self):
        from src.news.commands.youtube_command import YoutubeCommand
        video_data = {"url": "https://www.youtube.com/watch?v=abc123", "title": "T", "description": "", "channel": "C"}
        state = {"https://www.youtube.com/@test": "https://www.youtube.com/watch?v=abc123"}
        with patch("src.news.commands.youtube_command.load_config", return_value={"youtube_channels": ["https://www.youtube.com/@test"]}), \
             patch("src.news.commands.youtube_command._fetch_latest_video", return_value=video_data), \
             patch("src.news.commands.youtube_command._load_state", return_value=state):
            result = await YoutubeCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_for_new_video(self):
        from src.news.commands.youtube_command import YoutubeCommand
        video_data = {"url": "https://www.youtube.com/watch?v=newvideo", "title": "New", "description": "", "channel": "C"}
        state = {"https://www.youtube.com/@test": "https://www.youtube.com/watch?v=oldvideo"}
        formatted = {"text": "*New*\n\nRussian", "video": b"bytes"}
        with patch("src.news.commands.youtube_command.load_config", return_value={"youtube_channels": ["https://www.youtube.com/@test"]}), \
             patch("src.news.commands.youtube_command._fetch_latest_video", return_value=video_data), \
             patch("src.news.commands.youtube_command._load_state", return_value=state), \
             patch("src.news.commands.youtube_command._save_state"), \
             patch("src.news.commands.youtube_command._format", return_value=formatted):
            result = await YoutubeCommand().run_if_new()
        assert result == formatted

    def test_has_required_interface(self):
        from src.news.commands.youtube_command import YoutubeCommand
        from src.news.api.abstract_request_command import AbstractRequestCommand
        from src.news.api.abstract_news_command import AbstractNewsCommand
        assert issubclass(YoutubeCommand, AbstractRequestCommand)
        assert issubclass(YoutubeCommand, AbstractNewsCommand)
        assert YoutubeCommand.NAME == "youtube"
        assert isinstance(YoutubeCommand.LABEL, str)

    def test_format_drops_body_when_translation_fails(self):
        from src.news.commands.youtube_command import _format
        data = {"url": "u", "title": "English Title", "description": "English description", "channel": "C"}
        with patch("src.news.commands.youtube_command.rewrite_to_russian", return_value=None), \
             patch("src.news.commands.youtube_command.translate_to_russian", side_effect=lambda t: t), \
             patch("src.news.commands.youtube_command.download_youtube_video", return_value=None):
            result = _format(data)
        assert "English description" not in result["text"]
        assert result["text"].count("English Title") == 1

    def test_format_uses_translation_when_rewrite_fails(self):
        from src.news.commands.youtube_command import _format
        translations = {"English Title": "Русский заголовок", "English description": "Русское описание"}
        data = {"url": "u", "title": "English Title", "description": "English description", "channel": "C"}
        with patch("src.news.commands.youtube_command.rewrite_to_russian", return_value=None), \
             patch("src.news.commands.youtube_command.translate_to_russian", side_effect=lambda t: translations.get(t, t)), \
             patch("src.news.commands.youtube_command.download_youtube_video", return_value=None):
            result = _format(data)
        assert "Русское описание" in result["text"]
        assert "English" not in result["text"]

    def test_format_omits_body_when_no_description(self):
        from src.news.commands.youtube_command import _format
        data = {"url": "u", "title": "English Title", "description": "", "channel": "C"}
        with patch("src.news.commands.youtube_command.rewrite_to_russian", return_value=None), \
             patch("src.news.commands.youtube_command.translate_to_russian", side_effect=lambda t: "Русский заголовок"), \
             patch("src.news.commands.youtube_command.download_youtube_video", return_value=None):
            result = _format(data)
        assert result["text"] == "*Русский заголовок*\n\nu"


# ── InstagramCommand ──────────────────────────────────────────────────────────

class TestInstagramCommand:
    def test_is_request_command(self):
        from src.news.commands.instagram_command import InstagramCommand
        from src.news.api.abstract_request_command import AbstractRequestCommand
        assert issubclass(InstagramCommand, AbstractRequestCommand)

    def test_is_news_command(self):
        from src.news.commands.instagram_command import InstagramCommand
        from src.news.api.abstract_news_command import AbstractNewsCommand
        assert issubclass(InstagramCommand, AbstractNewsCommand)

    def test_has_name_and_label(self):
        from src.news.commands.instagram_command import InstagramCommand
        assert InstagramCommand.NAME == "instagram"
        assert InstagramCommand.LABEL

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_no_accounts(self):
        from src.news.commands.instagram_command import InstagramCommand
        with patch("src.news.commands.instagram_command.load_config", return_value={"instagram_accounts": []}):
            result = await InstagramCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_fetch_fails(self):
        from src.news.commands.instagram_command import InstagramCommand
        with patch("src.news.commands.instagram_command.load_config", return_value={"instagram_accounts": ["test_user"]}), \
             patch("src.news.commands.instagram_command._fetch_latest_post", return_value=None):
            result = await InstagramCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_same_shortcode(self, tmp_path):
        from src.news.commands.instagram_command import InstagramCommand
        state_file = tmp_path / "instagram_state.json"
        state_file.write_text('{"test_user": "ABC123"}')
        fake_post = {"shortcode": "ABC123", "username": "test_user", "caption": "hi",
                     "is_video": False, "video_url": None, "photos": [],
                     "post_url": "https://www.instagram.com/p/ABC123/"}
        with patch("src.news.commands.instagram_command._STATE_FILE", str(state_file)), \
             patch("src.news.commands.instagram_command.load_config", return_value={"instagram_accounts": ["test_user"]}), \
             patch("src.news.commands.instagram_command._fetch_latest_post", return_value=fake_post):
            result = await InstagramCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_when_new_post(self, tmp_path):
        from src.news.commands.instagram_command import InstagramCommand
        state_file = tmp_path / "instagram_state.json"
        state_file.write_text('{"test_user": "OLD123"}')
        fake_post = {"shortcode": "NEW456", "username": "test_user", "caption": "new post",
                     "is_video": False, "video_url": None, "photos": [],
                     "post_url": "https://www.instagram.com/p/NEW456/"}
        with patch("src.news.commands.instagram_command._STATE_FILE", str(state_file)), \
             patch("src.news.commands.instagram_command.load_config", return_value={"instagram_accounts": ["test_user"]}), \
             patch("src.news.commands.instagram_command._fetch_latest_post", return_value=fake_post):
            result = await InstagramCommand().run_if_new()
        assert result is not None

    def test_fetch_latest_post_skips_pinned(self):
        from src.news.commands.instagram_command import _fetch_latest_post
        pinned_node = {
            "shortcode": "PINNED1",
            "is_video": False,
            "pinned_for_users": [{"id": "123"}],
            "edge_media_to_caption": {"edges": [{"node": {"text": "pinned"}}]},
            "display_url": "",
            "edge_sidecar_to_children": {"edges": []},
        }
        new_node = {
            "shortcode": "NEW123",
            "is_video": False,
            "pinned_for_users": [],
            "edge_media_to_caption": {"edges": [{"node": {"text": "new post"}}]},
            "display_url": "",
            "edge_sidecar_to_children": {"edges": []},
        }
        api_response = {"data": {"user": {"edge_owner_to_timeline_media": {"edges": [
            {"node": pinned_node},
            {"node": new_node},
        ]}}}}
        mock_resp = type("R", (), {
            "status_code": 200,
            "json": lambda _: api_response,
            "raise_for_status": lambda _: None,
        })()
        with patch("src.news.commands.instagram_command.requests.get", return_value=mock_resp), \
             patch("src.news.commands.instagram_command._download_bytes", return_value=b"img"):
            result = _fetch_latest_post("test_user")
        assert result is not None
        assert result["shortcode"] == "NEW123"


# ── FacebookCommand ───────────────────────────────────────────────────────────

class TestFacebookCommand:
    def test_is_request_command(self):
        from src.news.commands.facebook_command import FacebookCommand
        from src.news.api.abstract_request_command import AbstractRequestCommand
        assert issubclass(FacebookCommand, AbstractRequestCommand)

    def test_is_news_command(self):
        from src.news.commands.facebook_command import FacebookCommand
        from src.news.api.abstract_news_command import AbstractNewsCommand
        assert issubclass(FacebookCommand, AbstractNewsCommand)

    def test_has_name_and_label(self):
        from src.news.commands.facebook_command import FacebookCommand
        assert FacebookCommand.NAME == "facebook"
        assert FacebookCommand.LABEL

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_no_pages(self):
        from src.news.commands.facebook_command import FacebookCommand
        with patch("src.news.commands.facebook_command.load_config", return_value={"facebook_pages": []}):
            result = await FacebookCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_fetch_fails(self):
        from src.news.commands.facebook_command import FacebookCommand
        with patch("src.news.commands.facebook_command.load_config", return_value={"facebook_pages": ["testpage"]}), \
             patch("src.news.commands.facebook_command._fetch_latest_post", return_value=None):
            result = await FacebookCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_none_when_same_post_id(self, tmp_path):
        from src.news.commands.facebook_command import FacebookCommand
        state_file = tmp_path / "facebook_state.json"
        state_file.write_text('{"testpage": "111"}')
        fake_post = {"post_id": "111", "page": "testpage", "text": "hi",
                     "images": [], "video": None, "post_url": ""}
        with patch("src.news.commands.facebook_command._STATE_FILE", str(state_file)), \
             patch("src.news.commands.facebook_command.load_config", return_value={"facebook_pages": ["testpage"]}), \
             patch("src.news.commands.facebook_command._fetch_latest_post", return_value=fake_post):
            result = await FacebookCommand().run_if_new()
        assert result is None

    @pytest.mark.asyncio
    async def test_run_if_new_returns_result_when_new_post(self, tmp_path):
        from src.news.commands.facebook_command import FacebookCommand
        state_file = tmp_path / "facebook_state.json"
        state_file.write_text('{"testpage": "111"}')
        fake_post = {"post_id": "222", "page": "testpage", "text": "new post",
                     "images": [], "video": None, "post_url": ""}
        with patch("src.news.commands.facebook_command._STATE_FILE", str(state_file)), \
             patch("src.news.commands.facebook_command.load_config", return_value={"facebook_pages": ["testpage"]}), \
             patch("src.news.commands.facebook_command._fetch_latest_post", return_value=fake_post):
            result = await FacebookCommand().run_if_new()
        assert result is not None


# ── State file paths ──────────────────────────────────────────────────────────
# Mechanical guard against re-posting the entire backlog: if a state path ever
# resolved inside src/ instead of the repo root, the live bot would read empty
# state on every restart and re-send everything it has ever seen.

class TestStateFilePaths:
    @pytest.mark.parametrize("module_name", [
        "facebook_command",
        "hkr_command",
        "iksurfmag_command",
        "instagram_command",
        "kitegirl_command",
        "youtube_command",
    ])
    def test_state_file_directory_is_repo_root(self, module_name):
        import importlib
        from pathlib import Path
        from src.shared.paths import ROOT

        mod = importlib.import_module(f"src.news.commands.{module_name}")
        state_path = Path(mod._STATE_FILE).resolve()
        assert state_path.parent == ROOT, (
            f"{module_name}._STATE_FILE resolves outside the repo root: {state_path}"
        )
