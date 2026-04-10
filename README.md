# hk_bot

A simple Telegram bot framework for wind/kite sports updates. Commands are auto-discovered plugins — add a file to `src/commands/` and it just works.

## Commands

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
├── src/
│   ├── bot.py                  # Entry point
│   ├── api/
│   │   ├── abstract_request_command.py   # Base class for all commands
│   │   ├── abstract_cron_command.py      # Mixin for scheduled commands
│   │   └── abstract_news_command.py      # Mixin for news-style commands
│   └── commands/               # Auto-discovered command plugins
│       ├── woo_command.py
│       ├── windguru_command.py
│       ├── hkr_command.py
│       └── iksurfmag_command.py
├── requirements.txt
└── .env.example
```

## Adding a Command

1. Create `src/commands/my_command.py`
2. Define a class extending `AbstractRequestCommand`
3. Set `NAME` (slash command) and `LABEL`, implement `async def run() -> str`

```python
from api.abstract_request_command import AbstractRequestCommand

class MyCommand(AbstractRequestCommand):
    NAME = "mycommand"
    LABEL = "My Command"

    async def run(self) -> str:
        return "Hello!"
```

The command is picked up automatically — no registration needed.

## Setup

```bash
# System dependency (required for voiceover)
apt-get install -y ffmpeg   # Debian/Ubuntu/Raspberry Pi OS

pip install -r requirements.txt
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN
python src/bot.py
```

> **Note:** On first run, `faster-whisper` will download the Whisper `tiny` model (~39 MB) to `~/.cache/` automatically. This only happens once.

## Deploy

Push to main — GitHub Actions deploys automatically to the LXC container.

## License

MIT
