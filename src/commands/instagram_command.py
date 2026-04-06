import os
import json
import time
import requests
from api.abstract_request_command import AbstractRequestCommand
from api.abstract_news_command import AbstractNewsCommand
from helpers.translation_helper import translate_to_russian

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../instagram_state.json")
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../config.json")
_API_URL = "https://www.instagram.com/api/v1/users/web_profile_info/"
_HEADERS = {"X-IG-App-ID": "936619743392459"}


class InstagramCommand(AbstractRequestCommand, AbstractNewsCommand):
    NAME = "instagram"
    LABEL = "Instagram 📸"

    async def run(self):
        accounts = _load_accounts()
        if not accounts:
            return "No Instagram accounts configured in config.json."
        post = _fetch(accounts[0]["username"])
        if post is None:
            return "Could not fetch Instagram post, please try again later."
        _save_state(accounts[0]["username"], post["shortcode"])
        return _format(post, accounts[0])

    async def run_if_new(self):
        for account in _load_accounts():
            post = _fetch(account["username"])
            if post is None:
                continue
            if _load_state().get(account["username"]) == post["shortcode"]:
                continue
            _save_state(account["username"], post["shortcode"])
            return _format(post, account)
        return None


def _load_accounts() -> list:
    try:
        with open(_CONFIG_FILE) as f:
            return json.load(f).get("instagram_accounts", [])
    except Exception:
        return []


def _fetch(username: str, retries: int = 2) -> dict | None:
    for attempt in range(retries + 1):
        try:
            r = requests.get(_API_URL, params={"username": username}, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            edges = r.json()["data"]["user"]["edge_owner_to_timeline_media"]["edges"]
            if not edges:
                return None
            node = edges[0]["node"]
            is_video = node.get("is_video", False)
            media_url = node.get("video_url") if is_video else node.get("display_url")
            image = None
            if media_url:
                img_r = requests.get(media_url, timeout=15)
                img_r.raise_for_status()
                image = img_r.content
            caption = ""
            cap_edges = node.get("edge_media_to_caption", {}).get("edges", [])
            if cap_edges:
                caption = cap_edges[0].get("node", {}).get("text", "")
            return {
                "shortcode": node["shortcode"],
                "caption": caption,
                "is_video": is_video,
                "image": image,
                "url": f"https://www.instagram.com/p/{node['shortcode']}/",
            }
        except Exception:
            if attempt == retries:
                return None
            time.sleep(2)


def _format(post: dict, account: dict) -> dict:
    name = account.get("name", account["username"])
    caption = translate_to_russian(post["caption"]) if post["caption"] else ""
    text = f"*{name}*\n\n{caption}\n\n[Пост]({post['url']})" if caption else f"*{name}*\n\n[Пост]({post['url']})"
    if post["image"]:
        key = "video" if post["is_video"] else "photos"
        value = post["image"] if post["is_video"] else [post["image"]]
        return {"text": text, key: value}
    return {"text": text}


def _load_state() -> dict:
    try:
        with open(_STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def _save_state(username: str, shortcode: str) -> None:
    try:
        state = _load_state()
        state[username] = shortcode
        with open(_STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception:
        pass
