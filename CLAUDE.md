# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A Telegram bot that allows managing Proxmox VE infrastructure (nodes, VMs, LXC containers) via chat commands. The bot communicates with Proxmox through a custom MCP (Model Context Protocol) server abstraction.

## Running and Development

```bash
# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env

# Run locally
python src/bot.py

# Deploy via Docker Compose
docker-compose -f deployment/docker-compose.yml up -d

# Deploy to Proxmox LXC
./deployment/deploy.sh
# Then inside container:
pct exec 100 -- python /root/src/bot.py
```

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | From Telegram BotFather |
| `PROXMOX_HOST` | Proxmox address, e.g. `192.168.1.100:8006` |
| `PROXMOX_USER` | e.g. `root@pam` |
| `PROXMOX_PASSWORD` | Proxmox password |
| `PROXMOX_VERIFY_SSL` | Set to `false` for self-signed certs |

## Architecture

Two main components:

**`src/bot.py`** — Telegram bot using `python-telegram-bot` v21.7. `ProxmoxBotHandler` class registers async command handlers (`/start`, `/help`, `/nodes`, `/vms`, `/containers`, `/status`). Handlers are currently scaffolded with placeholder responses and need to be wired to the MCP server.

**`proxmox_mcp/server.py`** — `ProxmoxMCPServer` class wraps the `proxmoxer` library. Provides `connect()`, `get_nodes()`, `get_vms(node)`, `get_containers(node)`, `get_system_status()`, `start_vm(node, vmid)`, `stop_vm(node, vmid)`. Use `create_mcp_server()` factory to instantiate from environment variables.

The integration between the bot and MCP server is the main gap left for development — the bot handlers need to call `ProxmoxMCPServer` methods and format responses for Telegram.

## Key Integration Pattern

```python
from proxmox_mcp.server import create_mcp_server

server = create_mcp_server()
if server.connect():
    nodes = server.get_nodes()
```
