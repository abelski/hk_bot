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

## CT 100 — hk-bot-ct
- **Purpose**: Runs the Telegram hello bot
- **Bot path**: `/root/hk_bot/src/bot.py`
- **Creds path**: `/root/hk_bot/.cred`
- **Service**: `hk-bot` (systemd, enabled, auto-restarts)
- **Python**: 3.10.12 at `/usr/bin/python3`
- **Deps installed**: `python-telegram-bot==21.7`, `python-dotenv==1.0.1`
- **SSH**: not installed (use `pct exec 100` via Proxmox host)

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
