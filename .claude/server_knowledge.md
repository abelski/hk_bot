# Server Knowledge

## Proxmox Host
- **IP**: 192.168.0.31
- **SSH**: `ssh root@192.168.0.31` (key-based, uses ~/.ssh/id_rsa)
- **API**: token `root@pam!arty`, value in `.cred` as `PROXMOX_TOKEN_VALUE`
- **Node name**: `raspberrypi` (arm64 / Raspberry Pi)
- **Storage**: `local` (dir type, ~294GB total, ~263GB free)

## Containers
| VMID | Hostname | IP | OS | Status |
|------|----------|----|----|--------|
| 100 | hk-bot-ct | 192.168.0.240 | Ubuntu Jammy 22.04 arm64 | running |

Both bots are deployed from the **same** repo (`hk_bot`) since the monorepo migration, each to
its own container with its own token. Deploy with `./deploy.sh news` or `./deploy.sh guard`.

## CT 100 — hk-bot-ct (news bot)
- **Purpose**: posts forecasts, leaderboards and rewritten news on cron
- **Launched as**: `/usr/bin/python3 -m src.news.bot` with `WorkingDirectory=/root/hk_bot`.
  It must run as a package from the repo root — a loose `python3 src/news/bot.py` cannot
  import `src.shared`, and `load_dotenv(".env")` would stop resolving.
- **Creds path**: `/root/hk_bot/.env` — **Service**: `hk-bot` (systemd, enabled, auto-restarts)
- **Python**: 3.10.12 at `/usr/bin/python3`
- **Config file**: `/root/hk_bot/config.json` (command-to-recipient mappings; edit + send `/reload`)
- **Systemd unit**: `/etc/systemd/system/hk-bot.service`, `EnvironmentFile=/root/hk_bot/.env`;
  `systemctl daemon-reload` after editing. `deploy.sh` and the CI both rewrite it.
- **SSH**: not installed (use `pct exec 100` via the Proxmox host)
- **State files** (`hkr_state.json` and friends) live in `/root/hk_bot/`, never under `src/`.
  They gate "have I already posted this" — if a code change makes those paths resolve anywhere
  else, the bot reads empty state and **re-posts its whole backlog to the live group**.
  Never let a deploy step push `*_state.json` to the server for the same reason.

## CT 101 — hk-guard (moderation bot)
- **Purpose**: deletes/warns on messages matching rules, in group `-1001713077893`
- **IP**: 192.168.0.241 — **Service**: `hk-guard` — **Bot**: `@hk_guard_bot`
- **Launched as**: `/usr/bin/python3 -m src.guard.bot`, `WorkingDirectory=/root/hk_guard`
- **Config**: `config.guard.json` in the repo is pushed to the container as `config.json`
- **Deps**: deliberately minimal (`requirements.guard.txt`) — 256MB RAM / 4GB disk, so the news
  bot's `faster-whisper`/`yt-dlp` must never be installed here
- Rules hot-reload: `load_config()` re-reads on every message, compiled patterns are cached by
  config content. Editing `config.json` in the container takes effect with no restart.

### Telegram traps that cause silent no-ops
- **Privacy mode is the #1 killer.** With it on, a bot receives only commands and replies, never
  ordinary members' messages — moderation then does nothing and logs nothing. Fix in BotFather:
  `/setprivacy` → Disable. Machine-checkable: `getMe` returns `can_read_all_group_messages`.
  A bot that is a chat **administrator** receives everything regardless, which is why the live
  bot works even though that flag still reads false.
- **Deleting needs explicit rights**: administrator with "Delete messages", or
  `message.delete()` raises and moderation degrades to logging.
- **A bot cannot DM a user who never pressed Start** — the first `send_message` to `ADMIN_ID`
  fails with `400 Chat not found`. Not a bug, and not fixable from the bot side.
- **Anonymous admins** arrive as `@GroupAnonymousBot` (id `1087968824`) with `sender_chat` set to
  the chat itself. `get_chat_member` cannot resolve them, so an admin exemption based on user id
  alone silently fails to cover them.

### Operational traps
- **httpx logs the bot token.** It logs full request URLs at INFO and every Telegram URL embeds
  the token, so it lands in `journalctl` in cleartext on every poll.
  `logging.getLogger("httpx").setLevel(logging.WARNING)` suppresses it.
- **macOS tar poisons a deploy.** Without `COPYFILE_DISABLE=1`, `tar` emits `._*` AppleDouble
  files beside every source file, and `pkgutil` autodiscovery then tries to import them.
  `deploy.sh` sets it; do not remove.
- **The Proxmox host wedged once** with every daemon accepting TCP but answering nothing (ssh
  reset at key exchange, empty replies on 8006). It was not fail2ban — a ban drops packets before
  the handshake. A reboot cleared it; disk and memory were fine. If it recurs, check `dmesg -T`
  for I/O errors first.

## Deployment pattern
```bash
# Copy file to CT 100
scp <file> root@192.168.0.31:/tmp/<file>
ssh root@192.168.0.31 "pct push 100 /tmp/<file> /root/hk_bot/<file>"

# Restart bot
ssh root@192.168.0.31 "pct exec 100 -- systemctl restart hk-bot"

# Check logs
ssh root@192.168.0.31 "pct exec 100 -- journalctl -u hk-bot -n 50 --no-pager"
```

## Templates available on local storage
- `ubuntu-jammy-20231124_arm64.tar.xz` (working)
- `debian-bookworm-20231124_arm64.tar.xz` (broken — network hook fails on create)

## Known issues
- Official Proxmox Debian 12 template is amd64-only, won't work on this arm64 Pi
- Proxmox REST API has no exec endpoint for LXC — must use `pct exec` via SSH
- `download_url` API endpoint returns 501 on this Proxmox version — use `aplinfo.post()` to download templates

## Groq API (rewrite_helper.py)
- Groq retires models without notice. `llama-3.3-70b-versatile` was silently removed
  (404 `model_not_found`), which made every `rewrite_to_russian()` call return None for
  an unknown period — posts degraded to raw MyMemory translation with nobody noticing,
  because the helper swallows all exceptions. Check `GET /openai/v1/models` when rewrite
  quality suddenly drops. As of 2026-09 no Llama chat models remain on Groq.
- `openai/gpt-oss-*` are reasoning models: they spend `max_tokens` on hidden reasoning
  first and return `content: ""` with `finish_reason: "length"` if the budget runs out.
  Must send `reasoning_effort: "low"` and keep `max_tokens` ≥ ~600, or every rewrite
  comes back empty (which looks identical to an API failure downstream).
- Cloudflare in front of api.groq.com rejects urllib's default User-Agent with
  403 `error code: 1010`. `requests` works; plain `urllib` needs an explicit UA header.
- Free tier rate-limits quickly on reasoning models — space out batch test calls ~15s.
