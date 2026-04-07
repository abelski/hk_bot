# hk_bot

A simple Telegram bot framework for wind/kite sports updates. Commands are auto-discovered plugins — add a file to `src/commands/` and it just works.

## Commands

| Command | Description |
|---------|-------------|
| `/woo` | WOO Leaderboard |
| `/windguru` | Wind Forecast |
| `/hkr` | HKR Reviews |
| `/iksurfmag` | IKSurf News |

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
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN
python src/bot.py
```

## Deploy

Push to main — GitHub Actions deploys automatically to the LXC container.

## License

MIT
