---
name: run-hk-bot
description: Run, start, smoke-test, or verify hk_bot — a Telegram polling bot for a kitesurfing community (news bot) plus its companion moderation bot (guard). Use when asked to run either bot, test it, confirm a change works, or check that startup succeeds.
---

hk_bot is a monorepo with two Python Telegram polling bots (`python-telegram-bot` v21.7):
`src/news/` (kitesurfing news/leaderboards, deployed as `hk-bot` on CT 100) and `src/guard/`
(chat moderation, deployed as `hk-guard` on CT 101). They share `src/shared/` (config loading,
path resolution) but have separate configs, requirements, and containers. Neither has an HTTP
interface; interacting with a live bot requires a real `TELEGRAM_BOT_TOKEN`. The smoke harness at
`.claude/skills/run-hk-bot/smoke.sh` verifies the things most PRs break: module imports for both
bots, news-bot startup/job scheduling, and the full unit test suite.

## Prerequisites

Python 3.10+. Install dependencies from repo root (news bot; guard uses
`requirements.guard.txt`, a much smaller subset for its 256MB container):

```bash
pip install -r requirements.txt
```

## Run (agent path) — smoke harness

Run this to confirm a change hasn't broken anything:

```bash
bash .claude/skills/run-hk-bot/smoke.sh
```

What it does:
1. Imports the news bot's command modules and `load_commands()` — verifies no import/syntax errors and that exactly 9 commands are discovered.
2. Imports `src.guard.bot` — verifies no import/syntax errors on the guard side.
3. Launches **both** bots the same way systemd does — `python3 -m src.news.bot` and `python3 -m src.guard.bot` (the guard bot from a temp dir staged like `deploy.sh`, with `config.guard.json` as its `config.json`) — with `TELEGRAM_BOT_TOKEN=fake:token`, and checks each reaches its `"Bot started"` log line (i.e., successfully loaded config, scheduled jobs, and reached polling). Each then fails at the Telegram API call — that is expected.
4. Runs `python3 -m pytest tests/ -q` (180 tests, ~7 s).

Expected output ends with:
```
OK: news bot reached polling stage (startup succeeded)
OK: guard bot reached polling stage (startup succeeded)
180 passed in ...s
=== All smoke checks passed ===
```

## Run (production path)

Requires a real `.env` with `TELEGRAM_BOT_TOKEN` set, run from the repo root:

```bash
python3 -m src.news.bot   # news bot — reads config.json
python3 -m src.guard.bot  # guard bot — reads config.json too (deploy.sh renames
                          # config.guard.json to config.json on CT 101)
```

Each bot polls Telegram, registers its handlers, and (news only) schedules cron jobs as
configured in `config.json`. Ctrl-C to stop.

In production, news runs as systemd service `hk-bot` on CT 100 and guard as `hk-guard` on CT 101
— separate Proxmox LXC containers, separate tokens, no shared poller.

## Unit tests only

```bash
python3 -m pytest tests/ -v
```

## Direct command invocation

News-bot commands are pure classes. To call one without starting the bot, run from the repo root:

```python
import asyncio
from src.news.commands.woo_command import WooCommand
result = asyncio.run(WooCommand().run())
print(result)
```

Requires real network access and valid credentials (for WOO, Instagram, etc.).

## Gotchas

- **`timeout` is not on macOS** — the smoke script uses `python3 subprocess.run(..., timeout=5)` instead of `timeout 5 ...` to work on both macOS and Linux.
- **`config.json` is required** — `load_config()` reads it from the repo root; if missing it returns `{"mappings": []}` silently. Both bots' `main()` now refuse to start on an empty config (`mappings` for news, `moderation` for guard) specifically so this can't fail silently in production.
- **`TELEGRAM_BOT_TOKEN` must look like `xxx:yyy`** — the Telegram library rejects tokens without a colon (raises `InvalidToken`) before reaching the polling stage. Use `fake:token` not `faketoken` in tests.
- **APScheduler logs at INFO** — news-bot startup emits several `Adding job tentatively` lines before `Bot started`; don't confuse APScheduler errors with bot errors.
- **Only package imports** — never add `sys.path.insert` or a flat `import bot`/`import commands`; under `-m src.news.bot` the module loads as `__main__`, and a stray `import src.news.bot` elsewhere would create a second module object with its own globals (mocks patched on one would silently not apply to the other).

## Troubleshooting

| Symptom | Fix |
|---|---|
| `InvalidToken` on startup | Token doesn't contain `:`. Use `fake:token` format. |
| Import error for `apscheduler` | `pip install "python-telegram-bot[job-queue]==21.7"` |
| `ModuleNotFoundError: src` | Run from repo root, not from `src/`. |
| `load_commands()` returns `0` instead of `9` | Something in `src/news/commands/__init__.py` still uses a flat `"commands."` prefix instead of `__name__` — check both places it's used (import and the `__module__` comparison). |
| Tests fail with `TELEGRAM_BOT_TOKEN not set` | Set any value: `TELEGRAM_BOT_TOKEN=x pytest ...` |
