import time
import requests
from datetime import datetime, timezone, timedelta
from api.abstract_request_command import AbstractRequestCommand
from api.abstract_cron_command import AbstractCronCommand

API_URL = "https://aky7qgzp1g.execute-api.us-east-1.amazonaws.com/v2/leaderboards/"
HEADERS = {
    "Authorization": "cbb1c29372536ad03c725af741cda7282767416ddca7aabbc50d3ed4f2c2ac81a38f26930ec7baf0a3d4c92f490da97f44107989b9e134c351c95335f139e8b0"
}

_MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def _flag_from_code(code):
    """Convert ISO 3166-1 alpha-2 country code to flag emoji (e.g. 'RU' → '🇷🇺')."""
    return "".join(chr(0x1F1E6 + ord(c) - ord("A")) for c in code.upper())


def _day_unix(days_offset=0):
    """Return (start, end) unix timestamps for today + days_offset (e.g. -1 = yesterday)."""
    now = datetime.now(timezone.utc)
    day = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=days_offset)
    start = int(day.timestamp())
    return start, start + 86400 - 1


class WooCommand(AbstractRequestCommand, AbstractCronCommand):
    NAME = "woo"
    LABEL = "WOO Leaderboard 🏄"

    async def run(self) -> str:
        from config_loader import load_config
        cfg = load_config()
        top_n = cfg.get("woo_top_limit", 3)
        fetch_limit = cfg.get("woo_fetch_limit", 100)
        countries = cfg.get("woo_countries", [])
        entries = _fetch_entries(fetch_limit)
        if entries is None:
            return "Could not fetch leaderboard, please try again later."
        country_data = {}
        for country in countries:
            code = country["code"]
            country_data[code] = {
                "today": _fetch_country_top1(code, days_offset=0),
                "alltime": _fetch_country_top1(code),
            }
        return _format_leaderboard(entries, top_n, countries, country_data)


def _fetch_entries(limit, retries=2):
    sd, ed = _day_unix(0)
    params = {
        "offset": 0,
        "limit": limit,
        "feature": "height",
        "game_type": "big_air",
        "start_date": sd,
        "end_date": ed,
    }
    for attempt in range(retries + 1):
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
            r.raise_for_status()
            return r.json()["items"]
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1)


def _fetch_country_top1(country_code, days_offset=None, retries=2):
    """Fetch top 1 for a country. If days_offset is None, fetches all-time."""
    params = {
        "offset": 0,
        "limit": 1,
        "feature": "height",
        "game_type": "big_air",
        "country_code": country_code,
    }
    if days_offset is not None:
        sd, ed = _day_unix(days_offset)
        params["start_date"] = sd
        params["end_date"] = ed
    for attempt in range(retries + 1):
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
            r.raise_for_status()
            items = r.json()["items"]
            return items[0] if items else None
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1)


def _rider_name(entry):
    return f"{entry['user']['first_name']} {entry['user']['last_name']}".strip()


def _format_leaderboard(entries, top_n, countries, country_data):
    now = datetime.now(timezone.utc)
    date_str = f"{now.day} {_MONTHS_RU[now.month]} {now.year}"
    header = f"Сегодня {date_str} лучшие по WOO 🏄"
    if not entries:
        return f"{header}\n\nРезультатов пока нет."
    lines = [header, ""]
    for e in entries[:top_n]:
        lines.append(f"#{e['rank']} · {_rider_name(e)} · {e['score']}m")
    if country_data:
        lines.append("")
        for country in countries:
            code = country["code"]
            data = country_data.get(code, {})
            flag = _flag_from_code(code)
            name = country["name"]
            today = data.get("today")
            alltime = data.get("alltime")
            if today:
                today_str = f"{_rider_name(today)} · {today['score']}m"
            else:
                today_str = "нет"
            if alltime:
                alltime_str = f"{_rider_name(alltime)} · {alltime['score']}m"
                lines.append(f"{flag} {name}: сегодня - {today_str} | рекорд - {alltime_str}")
            else:
                lines.append(f"{flag} {name}: сегодня - {today_str}")
    return "\n".join(lines)
