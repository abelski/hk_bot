import asyncio
import os
import json
import time

import requests
from facebook_scraper import get_posts

from api.abstract_request_command import AbstractRequestCommand
from api.abstract_news_command import AbstractNewsCommand
from config_loader import load_config
from helpers.rewrite_helper import rewrite_to_russian, strip_hashtags

_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "../../facebook_state.json"
)


class FacebookCommand(AbstractRequestCommand, AbstractNewsCommand):
    NAME = "facebook"
    LABEL = "Facebook 📘"

    async def run(self):
        pages = load_config().get("facebook_pages", [])
        for i, page in enumerate(pages):
            if i:
                await asyncio.sleep(3)
            data = await asyncio.to_thread(_fetch_latest_post, page)
            if data is not None:
                _save_state(page, data["post_id"])
                return await asyncio.to_thread(_format, data)
        return "Could not fetch Facebook posts, please try again later."

    async def run_if_new(self):
        pages = load_config().get("facebook_pages", [])
        state = _load_state()
        for i, page in enumerate(pages):
            if i:
                await asyncio.sleep(3)
            data = await asyncio.to_thread(_fetch_latest_post, page)
            if data is None:
                continue
            if data["post_id"] == state.get(page):
                continue
            _save_state(page, data["post_id"])
            return await asyncio.to_thread(_format, data)
        return None


def _fetch_latest_post(page_name: str, retries: int = 2) -> dict | None:
    for attempt in range(retries + 1):
        try:
            post = next(get_posts(page_name, pages=1), None)
            if post is None:
                return None
            images = post.get("images") or []
            return {
                "post_id": str(post.get("post_id", "")),
                "page": page_name,
                "text": post.get("text") or post.get("post_text") or "",
                "images": images,
                "video": post.get("video"),
                "post_url": post.get("post_url", ""),
            }
        except Exception:
            if attempt == retries:
                return None
            time.sleep(10 * (attempt + 1))
    return None


def _download_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def _format(data: dict) -> dict:
    raw = strip_hashtags(data["text"][:900]) if data["text"] else ""
    text = rewrite_to_russian(data["page"], raw) or raw or ""
    if data["video"]:
        video_bytes = _download_bytes(data["video"])
        if video_bytes:
            return {"text": text, "video": video_bytes}
    if data["images"]:
        photos = [b for url in data["images"][:4] if (b := _download_bytes(url))]
        if photos:
            return {"text": text, "photos": photos}
    return {"text": text}


def _load_state() -> dict:
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(page: str, post_id: str) -> None:
    state = _load_state()
    state[page] = post_id
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass
