import os
import json
import base64
import time
import requests
from commands.helpers.translate import translate_to_russian

_API_URL = "https://honestkitereviews.com/api/reviews"
_STATE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../hkr_state.json")

NAME = "hkr"
LABEL = "HKR Reviews 🪁"


async def run():
    data = _fetch()
    if data is None:
        return "Could not fetch review, please try again later."
    _save_state(data["id"])
    return _format(data)


async def run_if_new():
    data = _fetch()
    if data is None:
        return None
    if data["id"] == _load_state():
        return None
    _save_state(data["id"])
    return _format(data)


def _fetch(retries=2):
    for attempt in range(retries + 1):
        try:
            r = requests.get(_API_URL, timeout=10)
            r.raise_for_status()
            reviews = r.json()
            return reviews[0] if reviews else None
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1)


def _format(review) -> dict:
    safety = review.get("safetyStatus", "unknown").replace("-", " ").title()
    reviewer = f"{review['user']['firstName']} {review['user']['lastName']}".strip()
    text = (
        f"*{review['productName']}*\n"
        f"Brand: {review.get('brand', '?')} | Type: {review.get('productType', '?')}\n\n"
        f"{translate_to_russian(review.get('writeUp', ''))}\n\n"
        f"Safety: {safety} | Reviewed by {reviewer}"
    )
    photos = []
    for img in review.get("images", []):
        if isinstance(img, str) and "," in img:
            img = img.split(",", 1)[1]
        try:
            photos.append(base64.b64decode(img))
        except Exception:
            pass
    return {"text": text, "photos": photos}


def _load_state():
    try:
        with open(_STATE_FILE) as f:
            return json.load(f).get("last_id")
    except Exception:
        return None


def _save_state(review_id: int) -> None:
    try:
        with open(_STATE_FILE, "w") as f:
            json.dump({"last_id": review_id}, f)
    except Exception:
        pass
