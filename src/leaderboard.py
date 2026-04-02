import time
import requests
from datetime import datetime, timezone

API_URL = "https://aky7qgzp1g.execute-api.us-east-1.amazonaws.com/v2/leaderboards/"
HEADERS = {
    "Authorization": "cbb1c29372536ad03c725af741cda7282767416ddca7aabbc50d3ed4f2c2ac81a38f26930ec7baf0a3d4c92f490da97f44107989b9e134c351c95335f139e8b0"
}


def _today_unix():
    now = datetime.now(timezone.utc)
    start = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())
    end = start + 86400 - 1
    return start, end


def fetch_top3(retries=2):
    sd, ed = _today_unix()
    params = {
        "offset": 0,
        "limit": 3,
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


_MONTHS_RU = [
    "", "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
]


def format_top3(entries):
    now = datetime.now(timezone.utc)
    date_str = f"{now.day} {_MONTHS_RU[now.month]} {now.year}"
    header = f"Сегодня {date_str} лучшие по WOO 🏄"
    if not entries:
        return f"{header}\n\nРезультатов пока нет."
    lines = [header, ""]
    for e in entries:
        name = f"{e['user']['first_name']} {e['user']['last_name']}".strip()
        score = e["score"]
        lines.append(f"#{e['rank']} · {name} · {score}m")
    return "\n".join(lines)
