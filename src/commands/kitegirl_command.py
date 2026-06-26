import asyncio
import os
import json
import time

import requests

from api.abstract_request_command import AbstractRequestCommand
from api.abstract_news_command import AbstractNewsCommand
from config_loader import load_config
from helpers.rewrite_helper import rewrite_to_russian, strip_hashtags

_STATE_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "../../kitegirl_state.json"
)
_IG_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    ),
    "Accept": "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "X-IG-App-ID": "936619743392459",
}
_PROXY_URL = os.environ.get("INSTAGRAM_PROXY_URL", "").rstrip("/")
_PROXY_TOKEN = os.environ.get("INSTAGRAM_PROXY_TOKEN", "")
class KitegirlCommand(AbstractRequestCommand, AbstractNewsCommand):
    NAME = "kitegirl"
    LABEL = "Kite Girl 🪁"

    async def run(self):
        accounts = load_config().get("kitegirl_accounts", [])
        for i, username in enumerate(accounts):
            if i:
                await asyncio.sleep(3)
            data = await asyncio.to_thread(_fetch_latest_post, username)
            if data is not None:
                _save_state(username, data["shortcode"])
                return await asyncio.to_thread(_format, data)
        return "No kite girl posts found."

    async def run_if_new(self):
        accounts = load_config().get("kitegirl_accounts", [])
        state = _load_state()
        for i, username in enumerate(accounts):
            if i:
                await asyncio.sleep(3)
            data = await asyncio.to_thread(_fetch_latest_post, username)
            if data is None:
                continue
            if data["shortcode"] == state.get(username):
                continue
            _save_state(username, data["shortcode"])
            return await asyncio.to_thread(_format, data)
        return None


def _fetch_latest_post(username: str, retries: int = 2) -> dict | None:
    if _PROXY_URL:
        url = f"{_PROXY_URL}/?username={username}"
        headers = {"X-Proxy-Token": _PROXY_TOKEN}
    else:
        url = "https://i.instagram.com/api/v1/users/web_profile_info/"
        headers = _IG_HEADERS
    for attempt in range(retries + 1):
        try:
            r = requests.get(
                url,
                params=None if _PROXY_URL else {"username": username},
                headers=headers,
                timeout=15,
            )
            if r.status_code in (429, 401, 403):
                if attempt < retries:
                    time.sleep(10 * (attempt + 1))
                    continue
                return None
            r.raise_for_status()
            edges = r.json()["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
            if not edges:
                return None
            node = next(
                (e["node"] for e in edges if not e["node"].get("pinned_for_users")),
                edges[0]["node"],
            )
            shortcode = node["shortcode"]
            is_video = node.get("is_video", False)
            caption_edges = node.get("edge_media_to_caption", {}).get("edges", [])
            caption = caption_edges[0]["node"]["text"] if caption_edges else ""
            photos = []
            if not is_video:
                sidecar = node.get("edge_sidecar_to_children", {}).get("edges", [])
                if sidecar:
                    for child in sidecar[:4]:
                        cn = child["node"]
                        if not cn.get("is_video"):
                            photos.append(_download_bytes(cn.get("display_url", "")))
                else:
                    photos.append(_download_bytes(node.get("display_url", "")))
            return {
                "shortcode": shortcode,
                "username": username,
                "caption": caption,
                "is_video": is_video,
                "video_url": node.get("video_url") if is_video else None,
                "photos": [p for p in photos if p],
                "post_url": f"https://www.instagram.com/p/{shortcode}/",
            }
        except Exception:
            if attempt == retries:
                return None
            time.sleep(5)
    return None


def _download_bytes(url: str) -> bytes | None:
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.content
    except Exception:
        return None


def _format(data: dict) -> dict:
    raw = strip_hashtags(data["caption"][:900]) if data["caption"] else ""
    text = rewrite_to_russian(data["username"], raw) or raw or ""
    if data["is_video"] and data["video_url"]:
        video_bytes = _download_bytes(data["video_url"])
        if video_bytes:
            return {"text": text, "video": video_bytes}
    if data["photos"]:
        return {"text": text, "photos": data["photos"]}
    return {"text": text}


def _load_state() -> dict:
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(username: str, shortcode: str) -> None:
    state = _load_state()
    state[username] = shortcode
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass
