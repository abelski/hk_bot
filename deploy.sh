#!/usr/bin/env bash
# Push one bot's code to its container and restart it.
#
#   ./deploy.sh news   -> CT 100 (hk-bot)
#   ./deploy.sh guard  -> CT 101 (hk-guard)
#
# Does not touch .env on either container — both are already correct there,
# and this project deliberately has no CI job that would overwrite them.
set -euo pipefail

BOT="${1:-}"
case "$BOT" in
  news)
    HOST=root@192.168.0.31
    VMID=100
    BOT_DIR=/root/hk_bot
    SERVICE=hk-bot
    LOCAL_CONFIG=config.json
    LOCAL_REQUIREMENTS=requirements.txt
    DESCRIPTION="HK Telegram Bot"
    WATCHDOG_LINE="WatchdogSec=120"
    ;;
  guard)
    HOST=root@192.168.0.31
    VMID=101
    BOT_DIR=/root/hk_guard
    SERVICE=hk-guard
    LOCAL_CONFIG=config.guard.json
    LOCAL_REQUIREMENTS=requirements.guard.txt
    DESCRIPTION="hk-guard Telegram Bot"
    WATCHDOG_LINE=""
    ;;
  *)
    echo "Usage: $0 news|guard" >&2
    exit 1
    ;;
esac

cd "$(dirname "$0")"

TMP_TAR="/tmp/hk_bot_${BOT}_deploy.tar.gz"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$STAGE/src"
cp src/__init__.py "$STAGE/src/__init__.py"
cp -R src/shared "$STAGE/src/shared"
cp -R "src/$BOT" "$STAGE/src/$BOT"
cp "$LOCAL_CONFIG" "$STAGE/config.json"
cp "$LOCAL_REQUIREMENTS" "$STAGE/requirements.txt"
find "$STAGE" -name "__pycache__" -type d -exec rm -rf {} +

# COPYFILE_DISABLE stops macOS tar from emitting ._* AppleDouble files, which
# pkgutil would then try to import as modules.
COPYFILE_DISABLE=1 tar czf "$TMP_TAR" -C "$STAGE" .

scp -q "$TMP_TAR" "$HOST:/tmp/"
ssh "$HOST" "
  pct push $VMID /tmp/$(basename "$TMP_TAR") /tmp/deploy.tar.gz
  pct exec $VMID -- mkdir -p $BOT_DIR
  pct exec $VMID -- tar xzf /tmp/deploy.tar.gz -C $BOT_DIR
  pct exec $VMID -- rm /tmp/deploy.tar.gz
  pct exec $VMID -- pip3 install -q -r $BOT_DIR/requirements.txt
  pct exec $VMID -- bash -c 'cat > /etc/systemd/system/$SERVICE.service << EOF
[Unit]
Description=$DESCRIPTION
After=network.target

[Service]
Type=simple
WorkingDirectory=$BOT_DIR
ExecStart=/usr/bin/python3 -m src.$BOT.bot
EnvironmentFile=$BOT_DIR/.env
Restart=always
RestartSec=5
$WATCHDOG_LINE

[Install]
WantedBy=multi-user.target
EOF'
  pct exec $VMID -- systemctl daemon-reload
  pct exec $VMID -- systemctl restart $SERVICE
"
rm -f "$TMP_TAR"
sleep 6
ssh "$HOST" "pct exec $VMID -- systemctl is-active $SERVICE"
