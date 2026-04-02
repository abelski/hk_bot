# Telegram Bot with Proxmox MCP Integration

Manage Proxmox resources via Telegram bot with Model Context Protocol (MCP) support.

## Features

- 🤖 Telegram bot interface for Proxmox management
- 📦 Proxmox MCP (Model Context Protocol) server
- 🐳 Docker/Docker Compose deployment
- 🚀 Proxmox LXC container deployment support
- ⚙️ Easy configuration with `.env` file

## Project Structure

```
hk_bot/
├── src/
│   └── bot.py              # Main Telegram bot
├── proxmox_mcp/
│   ├── __init__.py
│   └── server.py           # Proxmox MCP server implementation
├── deployment/
│   ├── Dockerfile          # Docker image definition
│   ├── docker-compose.yml  # Docker Compose configuration
│   └── deploy.sh           # Proxmox deployment script
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md
```

## Requirements

- Python 3.9+
- Proxmox VE 7.0+
- Telegram Bot Token (from BotFather)
- Docker & Docker Compose (for containerized deployment)

## Installation

### 1. Clone and Setup

```bash
cd /Users/Artur_Belski/Documents/src/hk_bot
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` with your settings:

```bash
TELEGRAM_BOT_TOKEN=your_token_here
PROXMOX_HOST=192.168.1.100:8006
PROXMOX_USER=root@pam
PROXMOX_PASSWORD=your_password
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Running

### Local Development

```bash
python src/bot.py
```

### Docker Compose

```bash
docker-compose -f deployment/docker-compose.yml up -d
```

### Proxmox LXC Container Deployment

```bash
chmod +x deployment/deploy.sh
./deployment/deploy.sh
```

Then in the container:

```bash
pct exec 100 -- python /root/src/bot.py
```

## Bot Commands

- `/start` - Start the bot
- `/nodes` - List all Proxmox nodes
- `/vms` - List all virtual machines
- `/containers` - List all LXC containers
- `/status` - Get system status
- `/help` - Show help message

## Proxmox MCP Server

The MCP server provides programmatic access to Proxmox operations:

```python
from proxmox_mcp.server import create_mcp_server

server = create_mcp_server()
if server.connect():
    nodes = server.get_nodes()
    vms = server.get_vms()
    containers = server.get_containers()
```

## Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | `123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11` |
| `PROXMOX_HOST` | Proxmox server address | `192.168.1.100:8006` |
| `PROXMOX_USER` | Proxmox user | `root@pam` |
| `PROXMOX_PASSWORD` | Proxmox password | `password123` |
| `PROXMOX_VERIFY_SSL` | Verify SSL certificate | `false` |

## Development

### Adding New Bot Commands

Edit `src/bot.py` and add command handlers to the `ProxmoxBotHandler` class.

### Extending Proxmox MCP

Add new methods to `proxmox_mcp/server.py` `ProxmoxMCPServer` class.

## Troubleshooting

### Connection Issues

- Verify Proxmox credentials
- Check firewall rules
- Ensure Proxmox API is accessible

### Telegram Bot Not Responding

- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check internet connectivity
- Review logs for errors

## License

MIT

## Support

For issues and questions, open an issue on the repository.
