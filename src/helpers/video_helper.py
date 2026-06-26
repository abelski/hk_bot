import json
import os
import subprocess
import tempfile


def get_video_dimensions(video_bytes: bytes) -> tuple[int, int] | None:
    """Return (width, height) of a video using ffprobe. Returns None on failure."""
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
        f.write(video_bytes)
        tmp_path = f.name
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-select_streams", "v:0",
                tmp_path,
            ],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return None
        info = json.loads(result.stdout)
        streams = info.get("streams", [])
        if not streams:
            return None
        w = streams[0].get("width")
        h = streams[0].get("height")
        if w and h:
            return (int(w), int(h))
        return None
    except Exception:
        return None
    finally:
        os.unlink(tmp_path)
