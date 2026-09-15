#!/usr/bin/env bash
# Smoke-test script for hk_bot.
# Run from the repo root: bash .claude/skills/run-hk-bot/smoke.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
cd "$ROOT"

echo "=== [1/3] Verify imports and command loading ==="
TELEGRAM_BOT_TOKEN=fake:token python3 -c "
import sys
sys.path.insert(0, 'src')
from commands import load_commands
cmds = load_commands()
print('Commands:', [c.NAME for c in cmds])
from config_loader import load_config
cfg = load_config()
print('Config keys (first 5):', list(cfg.keys())[:5])
print('OK')
"

echo ""
echo "=== [2/3] Startup probe — should schedule jobs then fail at Telegram API ==="
# Start bot with fake token; it must print 'Bot started' before failing on Telegram
# Use Python subprocess with timeout (avoids relying on GNU timeout which isn't on macOS by default)
OUTPUT=$(python3 -c "
import subprocess, sys, os
env = {**os.environ, 'TELEGRAM_BOT_TOKEN': 'fake:token'}
r = subprocess.run(
    [sys.executable, '-c',
     'import sys; sys.path.insert(0, \"src\"); from bot import main; main()'],
    capture_output=True, text=True, timeout=5, env=env
)
print(r.stdout)
print(r.stderr)
" 2>&1 || true)

echo "$OUTPUT" | grep -q "Bot started" \
  && echo "OK: bot reached polling stage (startup succeeded)" \
  || { echo "FAIL: bot did not reach polling stage"; echo "$OUTPUT"; exit 1; }

echo ""
echo "=== [3/3] Unit tests ==="
python3 -m pytest tests/ -q --tb=short

echo ""
echo "=== All smoke checks passed ==="
