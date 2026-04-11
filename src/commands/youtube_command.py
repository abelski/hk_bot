import asyncio
import os
import json

import yt_dlp

from api.abstract_request_command import AbstractRequestCommand
from api.abstract_news_command import AbstractNewsCommand
from config_loader import load_config
from helpers.rewrite_helper import rewrite_to_russian
from helpers.translation_helper import translate_to_russian
from helpers.youtube_helper import download_youtube_video

_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "../../youtube_state.json"
)


class YoutubeCommand(AbstractRequestCommand, AbstractNewsCommand):
    NAME = "youtube"
    LABEL = "YouTube 📺"

    async def run(self):
        channels = load_config().get("youtube_channels", [])
        for channel_url in channels:
            data = await asyncio.to_thread(_fetch_latest_video, channel_url)
            if data is not None:
                _save_state(channel_url, data["url"])
                return await asyncio.to_thread(_format, data)
        return "Could not fetch YouTube videos, please try again later."

    async def run_if_new(self):
        channels = load_config().get("youtube_channels", [])
        state = _load_state()
        for channel_url in channels:
            data = await asyncio.to_thread(_fetch_latest_video, channel_url)
            if data is None:
                continue
            if data["url"] == state.get(channel_url):
                continue
            _save_state(channel_url, data["url"])
            return await asyncio.to_thread(_format, data)
        return None


def _fetch_latest_video(channel_url: str) -> dict | None:
    """Return metadata dict for the most recently published video on a channel, or None."""
    videos_url = channel_url.rstrip("/") + "/videos"
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": True,
        "playlist_items": "1",
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(videos_url, download=False)
        if not info or not info.get("entries"):
            return None
        entry = info["entries"][0]
        video_id = entry.get("id")
        if not video_id:
            return None
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        # Fetch full metadata to get description (extract_flat omits it)
        full_opts = {"quiet": True, "no_warnings": True}
        try:
            with yt_dlp.YoutubeDL(full_opts) as ydl:
                full_info = ydl.extract_info(video_url, download=False)
            description = full_info.get("description") or ""
            title = full_info.get("title") or entry.get("title", "")
        except Exception:
            description = ""
            title = entry.get("title", "")
        return {
            "url": video_url,
            "title": title,
            "description": description,
            "channel": info.get("channel") or info.get("title", channel_url),
        }
    except Exception:
        return None


def _format(data: dict) -> dict:
    rewritten = rewrite_to_russian(data["title"], data["description"])
    if rewritten is None:
        excerpt = data["description"][:500] if data["description"] else ""
        rewritten = translate_to_russian(excerpt) if excerpt else data["title"]
    title_ru = translate_to_russian(data["title"]) or data["title"]
    text = f"*{title_ru}*\n\n{rewritten}"
    video_bytes = download_youtube_video(data["url"])
    if video_bytes:
        return {"text": text, "video": video_bytes}
    return {"text": text + f"\n\n{data['url']}"}


def _load_state() -> dict:
    try:
        with open(_STATE_FILE) as f:
            return json.load(f).get("last_urls", {})
    except Exception:
        return {}


def _save_state(channel_url: str, video_url: str) -> None:
    state = _load_state()
    state[channel_url] = video_url
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump({"last_urls": state}, f)
    except Exception:
        pass
