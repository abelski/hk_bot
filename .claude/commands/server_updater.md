You are working with a Proxmox server. Read the current server knowledge from `.claude/server_knowledge.md`, then perform the requested task.

## How to interact with the server

SSH access:
```bash
ssh root@192.168.0.31                        # Proxmox host
pct exec 100 -- <command>                    # Run command in CT 100
pct push 100 <local_path> <remote_path>      # Copy file into CT 100
```

Proxmox API (Python):
```python
from dotenv import load_dotenv
load_dotenv('.cred')
import sys; sys.path.insert(0, '.')
from proxmox_mcp.server import create_mcp_server
server = create_mcp_server()
server.connect()
```

## Deployment protocol (ALWAYS follow this when deploying bot code)

**Step 1 — Ask for consent**
Before making any changes to the server, use AskUserQuestion to ask:
> "Update bot on server? This will deploy [describe what changed] to CT 100."
If the user says no, stop.

**Step 2 — Backup**
```bash
ssh root@192.168.0.31 "pct exec 100 -- cp /root/hk_bot/src/bot.py /root/hk_bot/src/bot.py.bak"
```

**Step 3 — Deploy**
```bash
scp <changed_files> root@192.168.0.31:/tmp/
ssh root@192.168.0.31 "pct push 100 /tmp/<file> /root/hk_bot/<file>"
```

**Step 4 — Restart**
```bash
ssh root@192.168.0.31 "pct exec 100 -- systemctl restart hk-bot"
sleep 3
ssh root@192.168.0.31 "pct exec 100 -- systemctl status hk-bot --no-pager"
```

**Step 5 — Verify**
Check logs for errors:
```bash
ssh root@192.168.0.31 "pct exec 100 -- journalctl -u hk-bot -n 20 --no-pager"
```
If the service is not running or logs show errors → go to rollback.

**Step 6 — Rollback (on any error)**
```bash
ssh root@192.168.0.31 "pct exec 100 -- cp /root/hk_bot/src/bot.py.bak /root/hk_bot/src/bot.py"
ssh root@192.168.0.31 "pct exec 100 -- systemctl restart hk-bot"
```
Then inform the user what went wrong.

## Your task

$ARGUMENTS

## After completing the task

Update `.claude/server_knowledge.md` with anything new learned.
