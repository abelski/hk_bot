# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

A monorepo with two Telegram bots for a kitesurfing community, each deployed to its own Proxmox
LXC container:

- **News bot** (`src/news/`) — posts wind forecasts, leaderboards, and rewritten news from
  several sources on a cron schedule and on-demand. Deployed as systemd service `hk-bot` on CT
  100.
- **Guard bot** (`src/guard/`) — moderates chat messages against configurable word/regex rules
  (delete/warn). Deployed as systemd service `hk-guard` on CT 101.

They share `src/shared/` (config loading, repo-root path resolution) but have separate configs,
requirements, containers, and bot tokens — never one poller on two tokens.

## Running and Development

```bash
# Install dependencies
pip install -r requirements.txt          # news bot
pip install -r requirements.guard.txt    # guard bot

# Copy and configure environment
cp .env.example .env

# Run locally, from the repo root (not from src/)
python -m src.news.bot
python -m src.guard.bot

# Deploy straight to a container (not via CI)
./deploy.sh news    # CT 100, service hk-bot
./deploy.sh guard   # CT 101, service hk-guard
```

## Required Environment Variables

| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | From Telegram BotFather — a distinct token per bot/container |
| `ADMIN_ID` | Telegram user id allowed to DM commands / receive startup notices |
| `GROQ_API_KEY` | News bot only — rewrite pipeline (Groq LLM) |
| `INSTAGRAM_PROXY_URL` / `INSTAGRAM_PROXY_TOKEN` | News bot only — Cloudflare Worker proxy, needed if the container's IP is blocked by Instagram |

## Architecture

**`src/shared/paths.py`** — `ROOT = Path(__file__).resolve().parents[2]`, the repo root on disk.
All six `*_state.json` files and both configs resolve through this — never re-derive a path
relative to `__file__` elsewhere, or a future move will silently break state tracking again.

**`src/shared/config_loader.py`** — `load_config()` reads `config.json` from `ROOT`. Returns
`{"mappings": []}` if the file is missing, on purpose: both bots' `main()` refuse to start on an
empty config so a bad deploy fails loudly instead of running silently empty.

**`src/news/bot.py`** — Telegram bot using `python-telegram-bot` v21.7. Dispatches slash/DM/
mention commands from `src/news/commands/` (auto-discovered plugins, see
`.claude/commands/add-command.md`) and schedules cron jobs from `config.json`'s `mappings`.
`/reload` re-reads config without a restart.

**`src/news/commands/__init__.py`** — `load_commands()` scans the package with
`pkgutil.iter_modules` and instantiates every `AbstractRequestCommand` subclass it finds, using
`__name__` (not `__package__`) as the import prefix.

**`src/guard/bot.py`** — Telegram bot that runs every group message through
`src/guard/moderation.py`'s compiled rules (`config.json`'s `moderation` key) and deletes/warns
on a match. `/reload` re-reads config (rules recompile automatically since `compile_rules` is
cached by config content, not called once at startup).

**`src/guard/moderation.py`** — pure text-matching logic, no Telegram dependency: `compile_rules`
+ `find_action`, unit-testable without a bot at all.

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

Both bots run as packages from the repo root, never as loose scripts — that is what makes
`src.shared` importable and keeps `load_dotenv(".env")` resolving:

```bash
python3 -m src.news.bot     # WorkingDirectory must be the repo root
python3 -m src.guard.bot
```

Anything that needs the repo root on disk asks `src/shared/paths.py` for it rather than
counting `..` from its own location:

```python
from src.shared.paths import ROOT
state_file = ROOT / "hkr_state.json"
```
