import os
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
