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

## Planning workflow

For anything bigger than a one-line fix: `/feature_analyst <request>` clarifies scope, writes a
numbered checklist plan to `plans/NNNN-<slug>.md`, and on approval hands off to `/ralph-implement`
— a bounded, resumable loop that implements, runs validation, and retries failures up to a budget
before marking the plan `blocked` for a human. Optional add-ons: `ralph-reviewer` (read-only diff
review between implementation and validation — not wired in by default), `uat-tester` (black-box
verification of a command via direct invocation, no codebase access), `spec-writer` (unused until
this project adopts a `specs/` convention). `triage`/`fix-issue-from-triage` do the same for a
backlog of reported issues once a tracker is plugged in (asks which one on first use). A trivial
change (typo, one-line fix with an obvious cause) skips this — plan overhead should never exceed
the change itself.

## Development Rules

- **Minimal changes:** Make the smallest possible change that achieves the goal. Avoid refactoring surrounding code.
- **Simple architecture:** Prefer the simplest solution. Do not introduce abstractions, layers, or patterns unless strictly necessary.
- **New dependencies:** Before adding any new tool, library, or external service, ask for consent first.
- **Unit tests:** Always write unit tests for new or modified logic.
- **Post-implementation checks:** After every implementation, verify the change works end-to-end (run tests, check logs, manually test the affected behaviour).
- **Backward compatibility:** Before changing a command or handler's behaviour, check who already depends on it (community users, scheduled jobs, other commands). Prefer additive changes over altering or removing existing behaviour.
- **Knowledge capture:** If a bug takes real time to diagnose, or something about the server/deploy/API behaves non-obviously, write it to `.claude/server_knowledge.md` so it isn't re-learned.
- **No duplicate pollers:** Before starting the bot locally, check whether an instance is already running (locally or on the deployed container) — two pollers on the same token race and cause Telegram 409 conflicts.
- **AI-generated content:** Never assert tests on exact AI-rewritten text (Groq output) — assert on structured effects (which command ran, what was sent, arguments) instead; exact-text assertions break on harmless rewording.
- **Git safety:** Commit locally whenever useful. Never `git push` without explicit, in-session user consent — a plan calling for a push is not consent. This is also enforced structurally by `.claude/hooks/block-git-push.sh`, not just this rule.
- **Skill/agent authoring:** New commands, skills, or agents live in this project's own `.claude/`, never `~/.claude/`. Convention: [docs/skill-authoring.md](docs/skill-authoring.md). Heavier patterns not yet adopted here: [docs/patterns.md](docs/patterns.md).

## Key Integration Pattern

```python
from proxmox_mcp.server import create_mcp_server

server = create_mcp_server()
if server.connect():
    nodes = server.get_nodes()
```
