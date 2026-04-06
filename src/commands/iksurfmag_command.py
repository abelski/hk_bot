import os
import json
import re
import time
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
from api.abstract_request_command import AbstractRequestCommand
from api.abstract_news_command import AbstractNewsCommand
from helpers.rewrite_helper import rewrite_to_russian
from helpers.translation_helper import translate_to_russian

_RSS_URL = "https://www.iksurfmag.com/kitesurfing-news/feed/"
_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../iksurfmag_state.json")
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; kitesurf-bot/1.0)"}
_NS = {
    "content": "http://purl.org/rss/1.0/modules/content/",
    "media": "http://search.yahoo.com/mrss/",
}


class IksurfmagCommand(AbstractRequestCommand, AbstractNewsCommand):
    NAME = "iksurfmag"
    LABEL = "IKSurf News 🪁"

    async def run(self):
        data = _fetch_latest()
        if data is None:
            return "Could not fetch news, please try again later."
        _save_state(data["url"])
        return _format(data)

    async def run_if_new(self):
        data = _fetch_latest()
        if data is None:
            return None
        if data["url"] == _load_state():
            return None
        _save_state(data["url"])
        return _format(data)


def _fetch_latest(retries: int = 2) -> dict | None:
    for attempt in range(retries + 1):
        try:
            r = requests.get(_RSS_URL, headers=_HEADERS, timeout=15)
            r.raise_for_status()
            root = ET.fromstring(r.content)
            channel = root.find("channel")
            if channel is None:
                return None
            item = channel.find("item")
            if item is None:
                return None
            return _parse_item(item)
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1)


def _fetch_article_data(url: str) -> dict:
    """Fetch the article page; extract body text and YouTube video URL.

    iksurfmag injects a raw <!DOCTYPE html> block inside .single-post.
    BeautifulSoup surfaces this as a nested <body> element.
    Article text lives in classless <p> tags inside that body, after
    the subscribe-promo <section> tags which are stripped first.
    The YouTube embed uses data-src (lazy-loaded), not src.
    """
    result = {"text": "", "video_url": None}
    try:
        r = requests.get(url, headers=_HEADERS, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # Text: classless <p> tags inside the injected <body> within .single-post
        body = soup.select_one(".single-post body")
        if body:
            for tag in body.select("section"):
                tag.decompose()
            paras = [
                p.get_text(strip=True)
                for p in body.find_all("p")
                if p.get_text(strip=True) and not p.get("class")
            ]
            result["text"] = "\n\n".join(paras)

        # Video: lazy-loaded YouTube iframe uses data-src, not src
        iframe = soup.find("iframe", attrs={"data-src": lambda s: s and "youtube" in s})
        if iframe:
            result["video_url"] = _youtube_watch_url(iframe.get("data-src", ""))
    except Exception:
        pass
    return result


def _parse_item(item) -> dict:
    title = (item.findtext("title") or "").strip()
    url = (item.findtext("link") or "").strip()

    # Fetch text and video URL from the actual article page
    article_data = _fetch_article_data(url)
    text = article_data["text"]
    video_url = article_data["video_url"]

    media_el = item.find("media:content", _NS)

    # Fallback video from RSS if page fetch failed
    if not video_url:
        if media_el is not None and media_el.get("medium") == "video":
            video_url = media_el.get("url")
        if not video_url:
            full_html = ""
            content_el = item.find("content:encoded", _NS)
            if content_el is not None and content_el.text:
                full_html = content_el.text
            if full_html:
                rss_soup = BeautifulSoup(full_html, "html.parser")
                iframe = rss_soup.find("iframe", src=lambda s: s and "youtube" in s)
                if iframe:
                    video_url = _youtube_watch_url(iframe.get("src", ""))

    # Fallback text from RSS content:encoded if page fetch returned nothing
    if not text:
        full_html = ""
        content_el = item.find("content:encoded", _NS)
        if content_el is not None and content_el.text:
            full_html = content_el.text
        else:
            full_html = item.findtext("description") or ""
        if full_html:
            text = BeautifulSoup(full_html, "html.parser").get_text(separator="\n", strip=True)

    # Image: only when no video
    image_url = None
    if not video_url and media_el is not None and media_el.get("medium") != "video":
        image_url = media_el.get("url")

    # Download image bytes
    image = None
    if image_url:
        try:
            img_r = requests.get(image_url, headers=_HEADERS, timeout=15)
            img_r.raise_for_status()
            image = img_r.content
        except Exception:
            pass

    return {"url": url, "title": title, "text": text, "image": image, "video_url": video_url}


def _youtube_watch_url(embed_src: str) -> str | None:
    """Convert a YouTube embed URL to a watch URL. Returns None if not a YouTube embed."""
    m = re.search(r"/embed/([a-zA-Z0-9_-]+)", embed_src)
    if m:
        return f"https://www.youtube.com/watch?v={m.group(1)}"
    return None


def _format(data: dict) -> dict:
    rewritten = rewrite_to_russian(data["title"], data["text"])
    if rewritten is None:
        excerpt = data["text"][:500] if data["text"] else ""
        rewritten = translate_to_russian(excerpt) if excerpt else data["title"]
    text = f"*{data['title']}*\n\n{rewritten}"
    if data.get("video_url"):
        text += f"\n\n{data['video_url']}"
    text += f"\n\n[Читать далее]({data['url']})"
    result = {"text": text}
    if data.get("image"):
        result["photos"] = [data["image"]]
    return result


def _load_state() -> str | None:
    try:
        with open(_STATE_FILE) as f:
            return json.load(f).get("last_url")
    except Exception:
        return None


def _save_state(url: str) -> None:
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump({"last_url": url}, f)
    except Exception:
        pass
