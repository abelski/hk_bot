---
name: run-hk-bot
description: Run, start, smoke-test, or verify hk_bot — a Telegram polling bot for a kitesurfing community. Use when asked to run the bot, test it, confirm a change works, or check that startup succeeds.
---

hk_bot is a Python Telegram polling bot (`python-telegram-bot` v21.7). It has no HTTP interface; interaction with the live bot requires a real `TELEGRAM_BOT_TOKEN`. The smoke harness at `.claude/skills/run-hk-bot/smoke.sh` verifies the three things most PRs break: module imports, startup/job scheduling, and unit tests.

## Prerequisites

Python 3.10+. Install dependencies from repo root:

```bash
pip install -r requirements.txt
```

## Run (agent path) — smoke harness

Run this to confirm a change hasn't broken anything:

```bash
bash .claude/skills/run-hk-bot/smoke.sh
```

What it does:
1. Imports all command modules and `load_commands()` — verifies no import/syntax errors.
2. Starts the bot with `TELEGRAM_BOT_TOKEN=fake:token` and checks that it reaches the `"Bot started"` log line (i.e., successfully loaded config, scheduled all cron jobs, and reached polling). It will then fail at the Telegram API call — that is expected.
3. Runs `python3 -m pytest tests/ -q` (119 tests, ~13 s).

Expected output ends with:
```
OK: bot reached polling stage (startup succeeded)
119 passed in 12.29s
=== All smoke checks passed ===
```

## Run (production path)

Requires a real `.env` with `TELEGRAM_BOT_TOKEN` set:

```bash
python3 src/bot.py
```

The bot polls Telegram, registers command/message handlers, and schedules cron jobs as configured in `config.json`. Ctrl-C to stop.

On the production server it runs as a systemd service (`hk-bot`) inside Proxmox LXC container 100.

## Unit tests only

```bash
python3 -m pytest tests/ -v
```

## Direct command invocation

Commands are pure classes. To call one without starting the bot:

```python
import sys, asyncio
sys.path.insert(0, 'src')
from commands.woo_command import WooCommand
result = asyncio.run(WooCommand().run())
print(result)
```

Requires real network access and valid credentials (for WOO, Instagram, etc.).

## Gotchas

- **`timeout` is not on macOS** — the smoke script uses `python3 subprocess.run(..., timeout=5)` instead of `timeout 5 ...` to work on both macOS and Linux.
- **`config.json` is required** — `load_config()` reads it from the repo root; if missing it returns `{}` silently, which can make commands produce empty results without errors.
- **`TELEGRAM_BOT_TOKEN` must look like `xxx:yyy`** — the Telegram library rejects tokens without a colon (raises `InvalidToken`) before reaching the polling stage. Use `fake:token` not `faketoken` in tests.
- **APScheduler logs at INFO** — startup emits several `Adding job tentatively` lines before `Bot started`; don't confuse APScheduler errors with bot errors.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `InvalidToken` on startup | Token doesn't contain `:`. Use `fake:token` format. |
| Import error for `apscheduler` | `pip install "python-telegram-bot[job-queue]==21.7"` |
| `ModuleNotFoundError: commands` | Run from repo root, not from `src/`. |
| Tests fail with `TELEGRAM_BOT_TOKEN not set` | Set any value: `TELEGRAM_BOT_TOKEN=x pytest ...` |
