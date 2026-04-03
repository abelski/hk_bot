# Feature: Daily Leaderboard Broadcast

## Context
The bot currently only sends leaderboard data reactively (on message / mention). This adds a proactive daily broadcast: at 23:00 UTC the bot fetches the day's top-3 and posts it to a configured Telegram chat. Uses `python-telegram-bot`'s built-in `JobQueue` (APScheduler) — no new infra needed.

## Decisions
- **Target chats:** `LEADERBOARD_CHAT_IDS` env var — comma-separated list of chat IDs (e.g. `-100111,-100222`)
- **Send time:** 23:00 UTC daily
- **Format:** reuse existing `format_top3()` from `src/leaderboard.py`
- **Scheduler:** in-process `JobQueue` via `python-telegram-bot[job-queue]` extra

## Scope
**In scope:**
- Add `send_daily_leaderboard` job function to `src/bot.py`
- Register job via `app.job_queue.run_daily()` in `main()`
- Add `LEADERBOARD_CHAT_IDS` env var (comma-separated) to loading block and `.env.example`
- Update `requirements.txt` to pull in JobQueue extra
- Unit test for the new job function

**Out of scope:**
- Changing the leaderboard format
- Admin commands to change send time at runtime

## Affected Files
| File | Change |
|------|--------|
| `requirements.txt` | Change `python-telegram-bot==21.7` → `python-telegram-bot[job-queue]==21.7` |
| `src/bot.py` | Add env var, new job function, register job in `main()` |
| `.env.example` | Document `LEADERBOARD_CHAT_IDS` |
| `tests/test_bot_handlers.py` | Add test class for `send_daily_leaderboard` |

## Implementation Steps

### Step 1 — Enable JobQueue in requirements
**File:** `requirements.txt` line 1

Change:
```
python-telegram-bot==21.7
```
to:
```
python-telegram-bot[job-queue]==21.7
```

**Verify:** `pip install -r requirements.txt` installs `apscheduler` as a transitive dep.

---

### Step 2 — Load LEADERBOARD_CHAT_IDS in bot.py
**File:** `src/bot.py`, after line 27 (after `BOT_REPO_URL = ...`)

Add:
```python
LEADERBOARD_CHAT_IDS = [
    cid.strip()
    for cid in os.getenv("LEADERBOARD_CHAT_IDS", "").split(",")
    if cid.strip()
]
```

---

### Step 3 — Add the job function
**File:** `src/bot.py`, add after `answer_mention()` (after line 54), before `update_command()`.

```python
async def send_daily_leaderboard(context: ContextTypes.DEFAULT_TYPE) -> None:
    if not LEADERBOARD_CHAT_IDS:
        logger.warning("LEADERBOARD_CHAT_IDS not set, skipping daily leaderboard")
        return
    entries = fetch_top3()
    if entries is None:
        logger.error("Daily leaderboard: failed to fetch top3")
        return
    text = format_top3(entries)
    for chat_id in LEADERBOARD_CHAT_IDS:
        await context.bot.send_message(chat_id=chat_id, text=text)
```

---

### Step 4 — Register the job in main()
**File:** `src/bot.py`, in `main()` after line 120 (`app = Application.builder()...build()`).

Add import at top of file (after line 9):
```python
from datetime import time as dt_time
from datetime import timezone
```

Add after the `app = ...` line:
```python
app.job_queue.run_daily(
    send_daily_leaderboard,
    time=dt_time(23, 0, 0, tzinfo=timezone.utc),
)
```

---

### Step 5 — Update .env.example
Add after the `TELEGRAM_BOT_TOKEN` line:
```
LEADERBOARD_CHAT_IDS=-100111111111,-100222222222
```

---

### Step 6 — Add unit test
**File:** `tests/test_bot_handlers.py`

Add new test class at the end:
```python
class TestSendDailyLeaderboard:
    @pytest.mark.asyncio
    async def test_sends_leaderboard_to_all_chats(self):
        import bot
        original = bot.LEADERBOARD_CHAT_IDS
        bot.LEADERBOARD_CHAT_IDS = ["-100111", "-100222"]
        ctx = MagicMock()
        ctx.bot.send_message = AsyncMock()
        entries = [{"rank": 1, "user": {"first_name": "A", "last_name": "B"}, "score": 10}]
        with patch("bot.fetch_top3", return_value=entries), \
             patch("bot.format_top3", return_value="leaderboard text"):
            from bot import send_daily_leaderboard
            await send_daily_leaderboard(ctx)
        assert ctx.bot.send_message.await_count == 2
        ctx.bot.send_message.assert_any_await(chat_id="-100111", text="leaderboard text")
        ctx.bot.send_message.assert_any_await(chat_id="-100222", text="leaderboard text")
        bot.LEADERBOARD_CHAT_IDS = original

    @pytest.mark.asyncio
    async def test_skips_when_no_chat_ids_set(self):
        import bot
        original = bot.LEADERBOARD_CHAT_IDS
        bot.LEADERBOARD_CHAT_IDS = []
        ctx = MagicMock()
        ctx.bot.send_message = AsyncMock()
        with patch("bot.fetch_top3") as mock_fetch:
            from bot import send_daily_leaderboard
            await send_daily_leaderboard(ctx)
        mock_fetch.assert_not_called()
        ctx.bot.send_message.assert_not_awaited()
        bot.LEADERBOARD_CHAT_IDS = original

    @pytest.mark.asyncio
    async def test_logs_error_when_fetch_fails(self):
        import bot
        original = bot.LEADERBOARD_CHAT_IDS
        bot.LEADERBOARD_CHAT_IDS = ["-100111"]
        ctx = MagicMock()
        ctx.bot.send_message = AsyncMock()
        with patch("bot.fetch_top3", return_value=None):
            from bot import send_daily_leaderboard
            await send_daily_leaderboard(ctx)
        ctx.bot.send_message.assert_not_awaited()
        bot.LEADERBOARD_CHAT_IDS = original
```

## Verification
```bash
# Install deps (confirm apscheduler is pulled in)
pip install -r requirements.txt

# Run tests
pytest tests/test_bot_handlers.py -v

# Manual: set LEADERBOARD_CHAT_ID in .env to a real chat ID, run bot,
# then temporarily change run_daily time to ~1 min from now to confirm message arrives.
```

## Edge Cases
| Scenario | Behaviour |
|----------|-----------|
| `LEADERBOARD_CHAT_IDS` empty/not set | Logs warning, skips silently |
| API returns None | Logs error, no message sent |
| Bot lacks permission to post in chat | `send_message` raises; exception propagates to JobQueue error handler (logs) |
