import asyncio
import time
import requests
from datetime import datetime, timezone
from api.abstract_request_command import AbstractRequestCommand

BASE_URL = "https://spot.thesurfr.app/api/proxy"

_MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


class SurfrCommand(AbstractRequestCommand):
    NAME = "surfr"
    LABEL = "Surfr Leaderboard 🪁"

    async def run(self) -> str:
        entries = await asyncio.to_thread(_fetch_leaderboard)
        if entries is None:
            return "Could not fetch leaderboard, please try again later."
        return _format_leaderboard(entries)


def _fetch_leaderboard(retries=2):
    params = {"period": "daily", "offset": 0}
    for attempt in range(retries + 1):
        try:
            r = requests.get(f"{BASE_URL}/leaderboard/height", params=params, timeout=10)
            r.raise_for_status()
            data = r.json()
            return data if isinstance(data, list) else []
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1)


def _rider_name(entry):
    return (entry.get("user") or {}).get("name") or "Unknown"


def _rider_score(entry):
    v = entry.get("value") or 0
    return round(v, 2) if isinstance(v, float) else v


def _flag_from_code(code):
    if not code or len(code) != 2:
        return ""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def _format_leaderboard(entries, top_n=5):
    now = datetime.now(timezone.utc)
    date_str = f"{now.day} {_MONTHS_RU[now.month]} {now.year}"
    header = f"Сегодня {date_str} лучшие по Surfr 🪁"
    if not entries:
        return f"{header}\n\nРезультатов пока нет."
    lines = [header, ""]
    for i, e in enumerate(entries[:top_n], 1):
        country = (e.get("user") or {}).get("country") or ""
        flag = _flag_from_code(country)
        prefix = f"{flag} " if flag else ""
        lines.append(f"#{i} · {prefix}{_rider_name(e)} · {_rider_score(e)}m")
    return "\n".join(lines)
