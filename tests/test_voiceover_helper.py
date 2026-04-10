import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../src"))


# ---------------------------------------------------------------------------
# _parse_vtt
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
# extract_subtitles
# ---------------------------------------------------------------------------

def test_extract_subtitles_returns_text_when_vtt_found(tmp_path):
    from helpers.youtube_helper import extract_subtitles

    vtt_content = "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nKite surfing\n"
    (tmp_path / "subs.en.vtt").write_text(vtt_content)

    class FakeYDL:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def download(self, urls):
            pass

    with patch("yt_dlp.YoutubeDL", FakeYDL), \
         patch("tempfile.TemporaryDirectory") as mock_tmp:
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        result = extract_subtitles("https://youtube.com/watch?v=test")

    assert result == "Kite surfing"


def test_extract_subtitles_returns_none_on_exception():
    from helpers.youtube_helper import extract_subtitles
    with patch("yt_dlp.YoutubeDL", side_effect=Exception("network error")):
        assert extract_subtitles("https://youtube.com/watch?v=test") is None


def test_extract_subtitles_returns_none_when_no_vtt(tmp_path):
    from helpers.youtube_helper import extract_subtitles

    class FakeYDL:
        def __init__(self, opts):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *a):
            pass
        def download(self, urls):
            pass

    with patch("yt_dlp.YoutubeDL", FakeYDL), \
         patch("tempfile.TemporaryDirectory") as mock_tmp:
        mock_tmp.return_value.__enter__ = lambda s: str(tmp_path)
        mock_tmp.return_value.__exit__ = MagicMock(return_value=False)
        result = extract_subtitles("https://youtube.com/watch?v=test")

    assert result is None


# ---------------------------------------------------------------------------
# _generate_tts
# ---------------------------------------------------------------------------

def test_generate_tts_returns_bytes():
    from helpers.voiceover_helper import _generate_tts
    import sys

    mock_tts = MagicMock()
    mock_tts.write_to_fp = lambda buf: buf.write(b"mp3data")
    mock_gtts_mod = MagicMock()
    mock_gtts_mod.gTTS = MagicMock(return_value=mock_tts)
    with patch.dict(sys.modules, {"gtts": mock_gtts_mod}):
        result = _generate_tts("Привет мир")

    assert result == b"mp3data"


def test_generate_tts_returns_none_on_exception():
    from helpers.voiceover_helper import _generate_tts
    import sys

    mock_gtts_mod = MagicMock()
    mock_gtts_mod.gTTS = MagicMock(side_effect=Exception("timeout"))
    with patch.dict(sys.modules, {"gtts": mock_gtts_mod}):
        assert _generate_tts("text") is None


# ---------------------------------------------------------------------------
# _mix_audio
# ---------------------------------------------------------------------------

def test_mix_audio_returns_bytes_on_success(tmp_path):
    from helpers.voiceover_helper import _mix_audio

    output_bytes = b"processed_video"

    def fake_run(cmd, **kwargs):
        output_path = cmd[-1]
        with open(output_path, "wb") as f:
            f.write(output_bytes)
        r = MagicMock()
        r.returncode = 0
        return r

    with patch("subprocess.run", side_effect=fake_run):
        result = _mix_audio(b"video", b"audio")

    assert result == output_bytes


def test_mix_audio_returns_none_on_ffmpeg_failure():
    from helpers.voiceover_helper import _mix_audio

    r = MagicMock()
    r.returncode = 1
    with patch("subprocess.run", return_value=r):
        assert _mix_audio(b"video", b"audio") is None


# ---------------------------------------------------------------------------
# transcribe_video
# ---------------------------------------------------------------------------

def test_transcribe_video_returns_text():
    from helpers.voiceover_helper import transcribe_video
    import sys

    mock_ffmpeg = MagicMock()
    mock_ffmpeg.returncode = 0
    seg = MagicMock()
    seg.text = "hello world"
    mock_model = MagicMock()
    mock_model.transcribe.return_value = ([seg], None)
    mock_fw_mod = MagicMock()
    mock_fw_mod.WhisperModel = MagicMock(return_value=mock_model)

    with patch("subprocess.run", return_value=mock_ffmpeg), \
         patch.dict(sys.modules, {"faster_whisper": mock_fw_mod}):
        result = transcribe_video(b"video_bytes")

    assert result == "hello world"


def test_transcribe_video_returns_none_when_ffmpeg_fails():
    from helpers.voiceover_helper import transcribe_video

    r = MagicMock()
    r.returncode = 1
    with patch("subprocess.run", return_value=r):
        assert transcribe_video(b"video") is None


def test_transcribe_video_returns_none_when_whisper_raises():
    from helpers.voiceover_helper import transcribe_video
    import sys

    mock_ffmpeg = MagicMock()
    mock_ffmpeg.returncode = 0
    mock_fw_mod = MagicMock()
    mock_fw_mod.WhisperModel = MagicMock(side_effect=Exception("model error"))

    with patch("subprocess.run", return_value=mock_ffmpeg), \
         patch.dict(sys.modules, {"faster_whisper": mock_fw_mod}):
        assert transcribe_video(b"video") is None


# ---------------------------------------------------------------------------
# process_youtube_video
# ---------------------------------------------------------------------------

def test_process_youtube_video_uses_subtitles_when_available():
    from helpers.voiceover_helper import process_youtube_video

    with patch("helpers.youtube_helper.extract_subtitles", return_value="subtitle text"), \
         patch("helpers.voiceover_helper.transcribe_video") as mock_whisper, \
         patch("helpers.voiceover_helper.add_russian_voiceover", return_value=b"processed"):
        result = process_youtube_video("https://youtube.com/watch?v=x", b"video")

    assert result == b"processed"
    mock_whisper.assert_not_called()


def test_process_youtube_video_falls_back_to_whisper():
    from helpers.voiceover_helper import process_youtube_video

    with patch("helpers.youtube_helper.extract_subtitles", return_value=None), \
         patch("helpers.voiceover_helper.transcribe_video", return_value="whisper text"), \
         patch("helpers.voiceover_helper.add_russian_voiceover", return_value=b"processed"):
        result = process_youtube_video("https://youtube.com/watch?v=x", b"video")

    assert result == b"processed"


def test_process_youtube_video_returns_none_when_no_transcript():
    from helpers.voiceover_helper import process_youtube_video

    with patch("helpers.youtube_helper.extract_subtitles", return_value=None), \
         patch("helpers.voiceover_helper.transcribe_video", return_value=None):
        result = process_youtube_video("https://youtube.com/watch?v=x", b"video")

    assert result is None


def test_process_youtube_video_returns_none_when_voiceover_fails():
    from helpers.voiceover_helper import process_youtube_video

    with patch("helpers.youtube_helper.extract_subtitles", return_value="text"), \
         patch("helpers.voiceover_helper.add_russian_voiceover", return_value=None):
        result = process_youtube_video("https://youtube.com/watch?v=x", b"video")

    assert result is None


# ---------------------------------------------------------------------------
# youtube_command._format — voiceover integration
# ---------------------------------------------------------------------------

def test_youtube_format_includes_original_video_when_voiceover_succeeds():
    from commands.youtube_command import _format

    data = {"url": "https://youtube.com/watch?v=x", "title": "Title", "description": ""}
    with patch("commands.youtube_command.rewrite_to_russian", return_value="текст"), \
         patch("commands.youtube_command.translate_to_russian", return_value="Заголовок"), \
         patch("commands.youtube_command.download_youtube_video", return_value=b"original"), \
         patch("commands.youtube_command.process_youtube_video", return_value=b"processed"):
        result = _format(data)

    assert result["video"] == b"processed"
    assert result["original_video"] == b"original"


def test_youtube_format_no_original_video_when_voiceover_fails():
    from commands.youtube_command import _format

    data = {"url": "https://youtube.com/watch?v=x", "title": "Title", "description": ""}
    with patch("commands.youtube_command.rewrite_to_russian", return_value="текст"), \
         patch("commands.youtube_command.translate_to_russian", return_value="Заголовок"), \
         patch("commands.youtube_command.download_youtube_video", return_value=b"original"), \
         patch("commands.youtube_command.process_youtube_video", return_value=None):
        result = _format(data)

    assert result["video"] == b"original"
    assert "original_video" not in result


# ---------------------------------------------------------------------------
# iksurfmag_command._format — voiceover integration
# ---------------------------------------------------------------------------

def test_iksurfmag_format_includes_original_video_when_voiceover_succeeds():
    from commands.iksurfmag_command import _format

    data = {"url": "u", "title": "T", "text": "B", "image": None,
            "video_url": "https://youtube.com/watch?v=x"}
    with patch("commands.iksurfmag_command.rewrite_to_russian", return_value="текст"), \
         patch("commands.iksurfmag_command.translate_to_russian", return_value="Заголовок"), \
         patch("commands.iksurfmag_command.download_youtube_video", return_value=b"original"), \
         patch("commands.iksurfmag_command.process_youtube_video", return_value=b"processed"):
        result = _format(data)

    assert result["video"] == b"processed"
    assert result["original_video"] == b"original"


def test_iksurfmag_format_no_original_video_when_voiceover_fails():
    from commands.iksurfmag_command import _format

    data = {"url": "u", "title": "T", "text": "B", "image": None,
            "video_url": "https://youtube.com/watch?v=x"}
    with patch("commands.iksurfmag_command.rewrite_to_russian", return_value="текст"), \
         patch("commands.iksurfmag_command.translate_to_russian", return_value="Заголовок"), \
         patch("commands.iksurfmag_command.download_youtube_video", return_value=b"original"), \
         patch("commands.iksurfmag_command.process_youtube_video", return_value=None):
        result = _format(data)

    assert result["video"] == b"original"
    assert "original_video" not in result
