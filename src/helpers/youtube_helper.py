import os
import re
import tempfile


def download_youtube_video(url: str) -> bytes | None:
    """Download a YouTube video and return its bytes. Returns None on failure.

    Selects the best progressive MP4 up to 720p to stay within Telegram's 50 MB limit.
    Requires yt-dlp to be installed.
    """
    try:
        import yt_dlp
    except ImportError:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "video.%(ext)s")
        ydl_opts = {
            "format": "best[ext=mp4][height<=720]/best[ext=mp4]/best",
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            files = os.listdir(tmpdir)
            if not files:
                return None
            with open(os.path.join(tmpdir, files[0]), "rb") as f:
                return f.read()
        except Exception:
            return None


def extract_subtitles(url: str) -> str | None:
    """Extract auto-generated English subtitles as plain text using yt-dlp. Returns None on failure."""
    try:
        import yt_dlp
    except ImportError:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["en"],
            "subtitlesformat": "vtt",
            "skip_download": True,
            "outtmpl": os.path.join(tmpdir, "subs"),
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            for fname in os.listdir(tmpdir):
                if fname.endswith(".vtt"):
                    with open(os.path.join(tmpdir, fname)) as f:
                        return _parse_vtt(f.read())
        except Exception:
            return None
    return None


def _parse_vtt(vtt_text: str) -> str | None:
    """Extract deduplicated plain text from WebVTT subtitle format."""
    seen = set()
    text_lines = []
    for line in vtt_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("WEBVTT") or "-->" in line or line.isdigit():
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line not in seen:
            seen.add(line)
            text_lines.append(line)
    return " ".join(text_lines) if text_lines else None
