#!/bin/bash
# Start cloudflared tunnel if not already running. Safe to run from cron or at login.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CLOUDFLARED="$SCRIPT_DIR/bin/cloudflared"
TUNNEL_NAME="avi-marketdata-tunnel"

if pgrep -x cloudflared >/dev/null 2>&1; then
  exit 0
fi
[ -x "$CLOUDFLARED" ] || exit 1
nohup "$CLOUDFLARED" tunnel run "$TUNNEL_NAME" >> "$SCRIPT_DIR/cloudflared.log" 2>&1 &
exit 0
