# hk_bot

A monorepo with two Telegram bots for a kitesurfing community:

- **`src/news/`** — wind/kite sports news and leaderboards. Commands are auto-discovered
  plugins — add a file to `src/news/commands/` and it just works. Deployed as systemd service
  `hk-bot` on Proxmox LXC container 100.
- **`src/guard/`** — chat moderation (delete/warn on rule matches). Deployed as systemd service
  `hk-guard` on Proxmox LXC container 101.

They share `src/shared/` (config loading, path resolution) but have separate `config.json`
(news) / `config.guard.json` (guard) files, separate `requirements.txt` /
`requirements.guard.txt`, separate containers, and separate bot tokens — no shared poller.

## Commands (news bot)

| Command | Description |
|---------|-------------|
| `/woo` | WOO Leaderboard |
| `/windguru` | Wind Forecast |
| `/hkr` | HKR Reviews |
| `/iksurfmag` | IKSurf News |
| `/youtube` | Latest video from configured YouTube channels |

### YouTube Russian Voiceover

When a YouTube video is fetched (via `/youtube` or embedded in `/iksurfmag`), the bot automatically:

1. Extracts auto-generated English subtitles via yt-dlp
2. Falls back to [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (`tiny` model, ~39 MB) if no subtitles exist
3. Translates the transcript to Russian via MyMemory (free)
4. Generates Russian TTS audio via [gTTS](https://github.com/pndurette/gTTS) (free, requires internet)
5. Mixes the TTS audio into the video using ffmpeg

Two messages are sent: the voiceover version (with caption) followed by the original. If any step fails, the original video is sent silently.

## Project Structure

```
hk_bot/
├── config.json                 # news bot config
├── config.guard.json           # guard bot config (deployed as config.json on CT 101)
├── requirements.txt            # news bot deps
├── requirements.guard.txt      # guard bot deps (small — CT 101 has 256MB RAM)
├── conftest.py                 # empty; lets bare `pytest` resolve `src...` imports too
├── deploy.sh                   # ./deploy.sh news | guard
├── src/
│   ├── __init__.py
│   ├── shared/                 # used by both bots
│   │   ├── paths.py            #   ROOT = repo root, for state files and config
│   │   └── config_loader.py    #   reads config.json from ROOT
│   ├── news/
│   │   ├── bot.py              # entry point: python -m src.news.bot
│   │   ├── api/
│   │   │   ├── abstract_request_command.py   # Base class for all commands
│   │   │   ├── abstract_cron_command.py      # Mixin for scheduled commands
│   │   │   └── abstract_news_command.py      # Mixin for news-style commands
│   │   ├── commands/            # Auto-discovered command plugins
│   │   │   ├── woo_command.py
│   │   │   ├── windguru_command.py
│   │   │   ├── hkr_command.py
│   │   │   └── iksurfmag_command.py
│   │   └── helpers/
│   └── guard/
│       ├── bot.py               # entry point: python -m src.guard.bot
│       └── moderation.py        # rule compiling/matching, no Telegram deps
└── tests/                       # flat, unique basenames across both bots
```

## Adding a Command (news bot)

1. Create `src/news/commands/my_command.py`
2. Define a class extending `AbstractRequestCommand`
3. Set `NAME` (slash command) and `LABEL`, implement `async def run() -> str`

```python
from src.news.api.abstract_request_command import AbstractRequestCommand

class MyCommand(AbstractRequestCommand):
    NAME = "mycommand"
    LABEL = "My Command"

    async def run(self) -> str:
        return "Hello!"
```

The command is picked up automatically — no registration needed.

## Setup

```bash
# System dependency (required for voiceover, news bot only)
apt-get install -y ffmpeg   # Debian/Ubuntu/Raspberry Pi OS

pip install -r requirements.txt   # or requirements.guard.txt for the guard bot
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN
python -m src.news.bot    # or: python -m src.guard.bot
```

> **Note:** On first run, `faster-whisper` will download the Whisper `tiny` model (~39 MB) to `~/.cache/` automatically. This only happens once.

## Deploy

`deploy.sh` pushes one bot's code straight to its container over SSH/`pct` and restarts its
systemd service — not via CI (this project has no CI job or secret that deploys the guard bot):

```bash
./deploy.sh news    # CT 100, service hk-bot
./deploy.sh guard   # CT 101, service hk-guard
```

Pushing to `main` also triggers `.github/workflows/deploy.yml`, which tests and deploys the
**news bot only** (paths-filtered to `src/news/`, `src/shared/`, `config.json`,
`requirements.txt`).

## License

MIT
