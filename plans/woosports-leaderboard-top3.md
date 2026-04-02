# Feature: WooSports Big Air Top-3 Leaderboard for Today

## Summary
Replace the bot's "Hello!" reply with today's top-3 big air height leaderboard entries fetched from `leaderboards.woosports.com`. Every message triggers a live fetch of today's rankings, showing rank, rider name, height, location, and kite. 2 retries on failure, then a user-facing error message.

## Decisions from Interview
- **Trigger**: Every incoming message (replaces the catch-all `hello` handler)
- **Date scope**: Today only — filter by date using Unix timestamps
- **Fields**: rank, name, height, location, kite
- **Error handling**: 2 retries, then send an error message to the user

---

## Key Technical Finding: API Discovery Required

The site is a **JavaScript SPA** — the HTML is empty on static fetch. The leaderboard data comes from a private backend API (not documented). Date filtering uses Unix timestamp params `sd` (start) and `ed` (end).

**One-time manual step before coding**: open the page in Chrome DevTools → Network tab → filter XHR/Fetch → load `https://leaderboards.woosports.com/?feature=height&game_type=big_air` → capture the API call URL, headers, and response shape.

Expected API shape (based on research):
```
GET https://<api-host>/v1/leaderboard?feature=height&game_type=big_air&sd=<unix>&ed=<unix>
```
Response likely contains a ranked list with fields: name, height, location, kite model.

---

## Scope

**In scope:**
- New `src/leaderboard.py` module: fetch today's top-3 from the discovered API endpoint
- Replace `hello` handler in `src/bot.py` with the leaderboard handler
- Retry logic: 2 attempts with a short delay, then error message
- Formatted Telegram reply

**Out of scope:**
- Proxmox/MCP integration (separate feature)
- Caching / scheduled refresh
- Any command other than the catch-all message handler
- Authentication / login to WooSports

---

## Acceptance Criteria
- Any message to the bot returns today's top-3 big air height entries
- Each entry shows: `#1 · Name · 12.4m · Location · Kite Model`
- If the site returns no data for today, the bot replies with a clear "no results" message
- On network failure: retries 2 times, then sends "Could not fetch leaderboard, please try again later"

---

## Affected Files

| File | Change type | Reason |
|------|-------------|--------|
| `src/leaderboard.py` | create | New module: API fetch, date math, retry logic, formatting |
| `src/bot.py` | modify | Replace `hello` handler with leaderboard handler |
| `requirements.txt` | modify | No new deps needed (`requests` already present) |

---

## Implementation Steps

### Step 1: API Discovery (manual — user does this once)
1. Open `https://leaderboards.woosports.com/?feature=height&game_type=big_air` in Chrome
2. Open DevTools → Network → filter to Fetch/XHR
3. Note the API endpoint URL, any `Authorization` headers, and the JSON response structure
4. Add discovered endpoint + headers as constants in `src/leaderboard.py`

### Step 2: Create `src/leaderboard.py`
```python
import time, requests
from datetime import datetime, timezone

API_URL = "<discovered endpoint>"  # fill in after Step 1
HEADERS = {}                       # fill in if auth header needed

def _today_unix():
    now = datetime.now(timezone.utc)
    start = int(datetime(now.year, now.month, now.day, tzinfo=timezone.utc).timestamp())
    end = start + 86400 - 1
    return start, end

def fetch_top3(retries=2) -> list[dict] | None:
    sd, ed = _today_unix()
    params = {"feature": "height", "game_type": "big_air", "sd": sd, "ed": ed}
    for attempt in range(retries + 1):
        try:
            r = requests.get(API_URL, params=params, headers=HEADERS, timeout=10)
            r.raise_for_status()
            entries = r.json()["results"][:3]   # adapt key to actual response shape
            return entries
        except Exception:
            if attempt == retries:
                return None
            time.sleep(1)

def format_top3(entries: list[dict]) -> str:
    if not entries:
        return "No big air height results for today yet."
    lines = []
    for i, e in enumerate(entries, 1):
        lines.append(f"#{i} · {e['name']} · {e['height']}m · {e['location']} · {e['kite']}")
    return "\n".join(lines)
```

### Step 3: Update `src/bot.py`
- Import `fetch_top3` and `format_top3` from `src.leaderboard`
- Replace the `hello` handler body:
```python
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    entries = fetch_top3()
    if entries is None:
        await update.message.reply_text("Could not fetch leaderboard, please try again later.")
    else:
        await update.message.reply_text(format_top3(entries))
```

---

## Edge Cases & Risks

| Scenario | Expected behaviour | Risk |
|----------|--------------------|------|
| API requires auth token | 401 errors → add discovered token to HEADERS | high — must be verified in Step 1 |
| No entries for today | Returns empty list → "No results yet" | low |
| API shape differs from assumption | KeyError → crashes | med — adapt field names after discovery |
| API endpoint changes | Fetch fails → retry → error | low |
| Rate limiting | 429 response → treat as failure, retry | low |

---

## Testing Plan
1. Run `python -c "from src.leaderboard import fetch_top3, format_top3; print(format_top3(fetch_top3()))"` directly
2. Start the bot locally (`python src/bot.py`) and send any message — should see today's top-3
3. Temporarily break the API URL → verify retry logic fires twice, then error message appears

---

## Open Questions
- **What is the actual API endpoint URL?** (Requires Step 1 browser devtools inspection)
- **Does the API require an Authorization header?** (e.g. Bearer token from the WooSports app)
- **What are the exact JSON field names?** (`name`, `height`, `location`, `kite` are assumed — need to verify from real response)
