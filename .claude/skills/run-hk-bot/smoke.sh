#!/usr/bin/env bash
# Smoke-test script for hk_bot's two bots (news + guard).
# Run from the repo root: bash .claude/skills/run-hk-bot/smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

# The bots' dependencies live in a venv, not in the system python. Prefer the local one,
# then the CI runner's (the runner host is PEP 668 externally-managed), then give up.
if   [ -x "$ROOT/.venv/bin/python" ]; then PY="$ROOT/.venv/bin/python"
elif [ -x /root/ci-venv/bin/python ]; then PY=/root/ci-venv/bin/python
else PY=python3
fi
echo "interpreter: $PY"

echo "=== [1/4] Verify imports and command loading (news) ==="
TELEGRAM_BOT_TOKEN=fake:token "$PY" -c "
from src.news.commands import load_commands
cmds = load_commands()
print('Commands:', [c.NAME for c in cmds])
assert len(cmds) == 9, f'expected 9 commands, got {len(cmds)}: {[c.NAME for c in cmds]}'
from src.shared.config_loader import load_config
cfg = load_config()
print('Config keys (first 5):', list(cfg.keys())[:5])
print('OK')
"

echo ""
echo "=== [2/4] Verify guard bot imports ==="
TELEGRAM_BOT_TOKEN=fake:token "$PY" -c "
import src.guard.bot
print('OK')
"

echo ""
echo "=== [3/4] Startup probes — packaged launch of both bots ==="
echo "--- news: -m src.news.bot, should schedule jobs then fail at Telegram API ---"
OUTPUT=$("$PY" -c "
import subprocess, sys, os
env = {**os.environ, 'TELEGRAM_BOT_TOKEN': 'fake:token'}
r = subprocess.run(
    [sys.executable, '-m', 'src.news.bot'],
    capture_output=True, text=True, timeout=5, env=env
)
print(r.stdout)
print(r.stderr)
" 2>&1 || true)

echo "$OUTPUT" | grep -q "Bot started" \
  && echo "OK: news bot reached polling stage (startup succeeded)" \
  || { echo "FAIL: news bot did not reach polling stage"; echo "$OUTPUT"; exit 1; }

echo ""
echo "--- guard: -m src.guard.bot, staged like deploy.sh (own config.json), same probe ---"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/src"
cp src/__init__.py "$STAGE/src/__init__.py"
cp -R src/shared "$STAGE/src/shared"
cp -R src/guard "$STAGE/src/guard"
cp config.guard.json "$STAGE/config.json"

OUTPUT=$("$PY" -c "
import subprocess, sys, os
env = {**os.environ, 'TELEGRAM_BOT_TOKEN': 'fake:token'}
r = subprocess.run(
    [sys.executable, '-m', 'src.guard.bot'],
    capture_output=True, text=True, timeout=5, env=env, cwd='$STAGE'
)
print(r.stdout)
print(r.stderr)
" 2>&1 || true)

echo "$OUTPUT" | grep -q "Bot started: hk-guard" \
  && echo "OK: guard bot reached polling stage (startup succeeded)" \
  || { echo "FAIL: guard bot did not reach polling stage"; echo "$OUTPUT"; exit 1; }

echo ""
echo "=== [4/4] Unit tests ==="
"$PY" -m pytest tests/ -q --tb=short

echo ""
echo "=== All smoke checks passed ==="
