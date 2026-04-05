import json
import os
import time
import requests
from datetime import datetime, timedelta, timezone
from api.abstract_request_command import AbstractRequestCommand
from api.abstract_cron_command import AbstractCronCommand

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "config.json")
_SPOT_PAGE_URL = "https://www.windguru.cz/{spot_id}"
_API_URL = "https://www.windguru.net/int/iapi.php"
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.windguru.cz/",
}
_DIRS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
         "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]
_MONTHS_RU = ["", "января", "февраля", "марта", "апреля", "мая", "июня",
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]

_LOCAL_DAY_START = 6
_LOCAL_DAY_END = 22


class WindguruCommand(AbstractRequestCommand, AbstractCronCommand):
    NAME = "windguru"
    LABEL = "Wind Forecast 🌬️"

    async def run(self) -> str:
        spots = _load_spots()
        if not spots:
            return "No spots configured. Add windguru_spots to config.json."

        parts = []
        for spot in spots:
            data = _fetch(spot["id"])
            if data is None:
                parts.append(f"🌬️ *{spot['name']}*\nНе удалось получить прогноз.")
                continue
            fcst = data.get("fcst")
            if not fcst:
                parts.append(f"🌬️ *{spot['name']}*\nДанные прогноза недоступны.")
                continue
            tz_offset = spot.get("tz_offset", 0)
            parts.append(_format(spot["name"], fcst, tz_offset))

        return "\n\n".join(parts)


def _load_spots():
    try:
        with open(_CONFIG_PATH) as f:
            return json.load(f).get("windguru_spots", [])
    except Exception:
        return []


def _fetch(spot_id, retries=2):
    session = requests.Session()
    session.headers.update(_HEADERS)
    try:
        session.get(_SPOT_PAGE_URL.format(spot_id=spot_id), timeout=15)
    except Exception:
        pass

    params = {
        "q": "forecast",
        "id_spot": spot_id,
        "id_model": 3,
        "runsno": 0,
        "initstr": "",
        "lang": "en",
        "cachefix": int(time.time()),
    }
    for attempt in range(retries + 1):
        try:
            r = session.get(_API_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()
            if data.get("return") == "error":
                return None
            return data
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1)


def _deg_to_dir(deg):
    return _DIRS[round(deg / 22.5) % 16]


def _wind_color(kn):
    if kn < 8:
        return "⚪"
    if kn < 13:
        return "🔵"
    if kn < 21:
        return "🟢"
    if kn < 29:
        return "🟡"
    return "🔴"


def _wind_stars(kn):
    if kn < 8:
        return "·"
    if kn < 13:
        return "⭐"
    if kn < 18:
        return "⭐⭐⭐"
    if kn < 26:
        return "⭐⭐⭐⭐⭐"
    if kn < 32:
        return "⭐⭐⭐"
    return "⭐"


def _format(spot_name, data, tz_offset=0):
    initdate_str = data.get("initdate", "")
    hours = data.get("hours", [])
    windspd = data.get("WINDSPD", [])
    gusts = data.get("GUST", [])
    winddir = data.get("WINDDIR", [])

    if not (initdate_str and hours):
        return f"🌬️ *{spot_name}*\nНет данных прогноза."

    try:
        init = datetime.strptime(initdate_str, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    except ValueError:
        return f"🌬️ *{spot_name}*\nОшибка формата данных."

    now_local = datetime.now(timezone.utc) + timedelta(hours=tz_offset)
    today_local = now_local.date()
    tomorrow_local = today_local + timedelta(days=1)

    buckets = {today_local: [], tomorrow_local: []}
    for i, h in enumerate(hours):
        slot_utc = init + timedelta(hours=int(h))
        slot_local = slot_utc + timedelta(hours=tz_offset)
        day = slot_local.date()
        if day not in buckets:
            continue
        if not (_LOCAL_DAY_START <= slot_local.hour <= _LOCAL_DAY_END):
            continue
        spd = round(windspd[i]) if i < len(windspd) else None
        gust = round(gusts[i]) if i < len(gusts) else None
        direction = _deg_to_dir(winddir[i]) if i < len(winddir) else "?"
        buckets[day].append((slot_local.hour, direction, spd, gust))

    lines = [f"🌬️ *{spot_name}*"]
    for day, label in [(today_local, "Сегодня"), (tomorrow_local, "Завтра")]:
        slots = buckets[day]
        date_str = f"{day.day} {_MONTHS_RU[day.month]}"
        lines.append(f"\n📅 *{label}* — {date_str}")
        if not slots:
            lines.append("  нет данных")
            continue
        for hour, direction, spd, gust in slots:
            if spd is None:
                continue
            color = _wind_color(spd)
            stars = _wind_stars(spd)
            gust_str = f"↑{gust}kn" if gust is not None else ""
            lines.append(f"{color} `{hour:02d}:00`  {direction:<3}  {spd}kn {gust_str}  {stars}")

    return "\n".join(lines)
