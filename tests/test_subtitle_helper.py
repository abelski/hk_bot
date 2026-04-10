import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))


# ---------------------------------------------------------------------------
# _parse_vtt (plain text, used by extract_subtitles)
# ---------------------------------------------------------------------------

def test_parse_vtt_returns_clean_text():
    from helpers.youtube_helper import _parse_vtt
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nHello <c>world</c>\n\nHello world\n"
    assert _parse_vtt(vtt) == "Hello world"


def test_parse_vtt_deduplicates_lines():
    from helpers.youtube_helper import _parse_vtt
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nSame line\n\n00:00:02.000 --> 00:00:03.000\nSame line\n"
    assert _parse_vtt(vtt) == "Same line"


def test_parse_vtt_empty_returns_none():
    from helpers.youtube_helper import _parse_vtt
    assert _parse_vtt("WEBVTT\n\n") is None


def test_parse_vtt_strips_inline_tags():
    from helpers.youtube_helper import _parse_vtt
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\n<00:00:01.500><c>Kite</c> surfing\n"
    assert _parse_vtt(vtt) == "Kite surfing"


# ---------------------------------------------------------------------------
# _parse_vtt_segments (timing-aware, used by subtitle burn-in)
# ---------------------------------------------------------------------------

def test_parse_vtt_segments_extracts_timing():
    from helpers.subtitle_helper import _parse_vtt_segments
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:04.000\nHello world\n"
    segs = _parse_vtt_segments(vtt)
    assert len(segs) == 1
    assert segs[0] == ("00:00:01,000", "00:00:04,000", "Hello world")


def test_parse_vtt_segments_deduplicates():
    from helpers.subtitle_helper import _parse_vtt_segments
    vtt = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nSame\n\n00:00:02.000 --> 00:00:03.000\nSame\n"
    segs = _parse_vtt_segments(vtt)
    assert len(segs) == 1


def test_parse_vtt_segments_empty():
    from helpers.subtitle_helper import _parse_vtt_segments
    assert _parse_vtt_segments("WEBVTT\n\n") == []


# ---------------------------------------------------------------------------
# _vtt_time_to_srt / _seconds_to_srt
# ---------------------------------------------------------------------------

def test_vtt_time_to_srt():
    from helpers.subtitle_helper import _vtt_time_to_srt
    assert _vtt_time_to_srt("00:00:01.500") == "00:00:01,500"


def test_seconds_to_srt():
    from helpers.subtitle_helper import _seconds_to_srt
    assert _seconds_to_srt(61.5) == "00:01:01,500"
    assert _seconds_to_srt(3661.25) == "01:01:01,250"


# ---------------------------------------------------------------------------
# extract_subtitles_vtt
# ---------------------------------------------------------------------------

def test_extract_subtitles_vtt_returns_raw_vtt(tmp_path):
    from helpers.youtube_helper import extract_subtitles_vtt

    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nKite surfing\n"
    (tmp_path / "subs.en.vtt").write_text(vtt_content)

    class FakeYDL:
        def __init__(self, opts): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def download(self, urls): pass

    with patch("yt_dlp.YoutubeDL", FakeYDL), \
         patch("tempfile.TemporaryDirectory") as mock_tmp:
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        result = extract_subtitles_vtt("https://youtube.com/watch?v=test")

    assert result == vtt_content


def test_extract_subtitles_vtt_returns_none_on_exception():
    from helpers.youtube_helper import extract_subtitles_vtt
    with patch("yt_dlp.YoutubeDL", side_effect=Exception("fail")):
        assert extract_subtitles_vtt("https://youtube.com/watch?v=test") is None


# ---------------------------------------------------------------------------
# burn_subtitles
# ---------------------------------------------------------------------------

def test_burn_subtitles_returns_bytes_on_success(tmp_path):
    from helpers.subtitle_helper import burn_subtitles

    output_bytes = b"burned_video"

    def fake_run(cmd, **kwargs):
        output_path = cmd[-1]
        with open(output_path, "wb") as f:
            f.write(output_bytes)
        r = MagicMock()
        r.returncode = 0
        return r

    with patch("subprocess.run", side_effect=fake_run):
        result = burn_subtitles(b"video", "1\n00:00:01,000 --> 00:00:02,000\nПривет\n")

    assert result == output_bytes


def test_burn_subtitles_returns_none_on_ffmpeg_failure():
    from helpers.subtitle_helper import burn_subtitles

    r = MagicMock()
    r.returncode = 1
    with patch("subprocess.run", return_value=r):
        assert burn_subtitles(b"video", "1\n00:00:01,000 --> 00:00:02,000\nПривет\n") is None


# ---------------------------------------------------------------------------
# _whisper_to_translated_srt
# ---------------------------------------------------------------------------

def test_whisper_to_translated_srt_returns_srt():
    from helpers.subtitle_helper import _whisper_to_translated_srt
    import sys

    mock_ffmpeg = MagicMock()
    mock_ffmpeg.returncode = 0
    seg = MagicMock()
    seg.text = "hello"
    seg.start = 1.0
    seg.end = 3.0
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([seg], None)
    mock_fw_mod = MagicMock()
    mock_fw_mod.WhisperModel = MagicMock(return_value=mock_model)

    with patch("subprocess.run", return_value=mock_ffmpeg), \
         patch.dict(sys.modules, {"faster_whisper": mock_fw_mod}), \
         patch("helpers.subtitle_helper.translate_to_russian", return_value="привет"):
        result = _whisper_to_translated_srt(b"video")

    assert "00:00:01,000 --> 00:00:03,000" in result
    assert "привет" in result


def test_whisper_to_translated_srt_returns_none_when_ffmpeg_fails():
    from helpers.subtitle_helper import _whisper_to_translated_srt

    r = MagicMock()
    r.returncode = 1
    with patch("subprocess.run", return_value=r):
        assert _whisper_to_translated_srt(b"video") is None


# ---------------------------------------------------------------------------
# process_youtube_video
# ---------------------------------------------------------------------------

def test_process_youtube_video_uses_vtt_when_available():
    from helpers.subtitle_helper import process_youtube_video

    with patch("helpers.youtube_helper.extract_subtitles_vtt", return_value="WEBVTT\n..."), \
         patch("helpers.subtitle_helper._vtt_to_translated_srt", return_value="srt content"), \
         patch("helpers.subtitle_helper._whisper_to_translated_srt") as mock_whisper, \
         patch("helpers.subtitle_helper.burn_subtitles", return_value=b"burned"):
        result = process_youtube_video("https://youtube.com/watch?v=x", b"video")

    assert result == b"burned"
    mock_whisper.assert_not_called()


def test_process_youtube_video_falls_back_to_whisper():
    from helpers.subtitle_helper import process_youtube_video

    with patch("helpers.youtube_helper.extract_subtitles_vtt", return_value=None), \
         patch("helpers.subtitle_helper._whisper_to_translated_srt", return_value="srt"), \
         patch("helpers.subtitle_helper.burn_subtitles", return_value=b"burned"):
        result = process_youtube_video("https://youtube.com/watch?v=x", b"video")

    assert result == b"burned"


def test_process_youtube_video_returns_none_when_no_subtitles():
    from helpers.subtitle_helper import process_youtube_video

    with patch("helpers.youtube_helper.extract_subtitles_vtt", return_value=None), \
         patch("helpers.subtitle_helper._whisper_to_translated_srt", return_value=None):
        assert process_youtube_video("https://youtube.com/watch?v=x", b"video") is None


# ---------------------------------------------------------------------------
# youtube_command._format — integration
# ---------------------------------------------------------------------------

def test_youtube_format_uses_processed_video_when_subtitles_succeed():
    from commands.youtube_command import _format

    data = {"url": "https://youtube.com/watch?v=x", "title": "Title", "description": ""}
    with patch("commands.youtube_command.rewrite_to_russian", return_value="текст"), \
         patch("commands.youtube_command.translate_to_russian", return_value="Заголовок"), \
         patch("commands.youtube_command.download_youtube_video", return_value=b"original"), \
         patch("commands.youtube_command.process_youtube_video", return_value=b"burned"):
        result = _format(data)

    assert result["video"] == b"burned"
    assert "original_video" not in result


def test_youtube_format_falls_back_to_original_when_subtitles_fail():
    from commands.youtube_command import _format

    data = {"url": "https://youtube.com/watch?v=x", "title": "Title", "description": ""}
    with patch("commands.youtube_command.rewrite_to_russian", return_value="текст"), \
         patch("commands.youtube_command.translate_to_russian", return_value="Заголовок"), \
         patch("commands.youtube_command.download_youtube_video", return_value=b"original"), \
         patch("commands.youtube_command.process_youtube_video", return_value=None):
        result = _format(data)

    assert result["video"] == b"original"
    assert "original_video" not in result
