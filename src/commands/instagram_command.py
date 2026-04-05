import os
import json
import time
import requests
import instaloader
from api.abstract_request_command import AbstractRequestCommand
from api.abstract_news_command import AbstractNewsCommand
from helpers.translation_helper import translate_to_russian

_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../instagram_state.json")
_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../config.json")


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
            L = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                download_geotags=False,
                download_comments=False,
                save_metadata=False,
                post_metadata_txt_pattern="",
            )
            profile = instaloader.Profile.from_username(L.context, username)
            post = next(profile.get_posts())
            img = requests.get(post.url, timeout=15)
            img.raise_for_status()
            return {
                "shortcode": post.shortcode,
                "caption": post.caption or "",
                "image": img.content,
                "url": f"https://www.instagram.com/p/{post.shortcode}/",
            }
        except StopIteration:
            return None
        except Exception:
            if attempt == retries:
                return None
            time.sleep(2)


def _format(post: dict, account: dict) -> dict:
    name = account.get("name", account["username"])
    caption = translate_to_russian(post["caption"]) if post["caption"] else ""
    text = f"*{name}*\n\n{caption}\n\n[Пост]({post['url']})" if caption else f"*{name}*\n\n[Пост]({post['url']})"
    return {"text": text, "photos": [post["image"]]}


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
