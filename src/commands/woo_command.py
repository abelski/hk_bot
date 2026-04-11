import time
import requests
from datetime import datetime, timezone
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
        return _format_leaderboard(entries, top_n, countries)


def _today_unix():
    now = datetime.now(timezone.utc)
    start = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())
    end = start + 86400 - 1
    return start, end


def _fetch_entries(limit, retries=2):
    sd, ed = _today_unix()
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


def _format_leaderboard(entries, top_n, countries):
    now = datetime.now(timezone.utc)
    date_str = f"{now.day} {_MONTHS_RU[now.month]} {now.year}"
    header = f"Сегодня {date_str} лучшие по WOO 🏄"
    if not entries:
        return f"{header}\n\nРезультатов пока нет."
    lines = [header, ""]
    for e in entries[:top_n]:
        name = f"{e['user']['first_name']} {e['user']['last_name']}".strip()
        score = e["score"]
        lines.append(f"#{e['rank']} · {name} · {score}m")
    if countries:
        lines.append("")
        for country in countries:
            flag = country["flag"]
            champion = next(
                (e for e in entries
                 if flag in f"{e['user']['first_name']} {e['user']['last_name']}"),
                None,
            )
            if champion:
                cname = f"{champion['user']['first_name']} {champion['user']['last_name']}".strip()
                lines.append(f"{flag} {country['name']} чемпион - {cname} - {champion['score']}m")
    return "\n".join(lines)
