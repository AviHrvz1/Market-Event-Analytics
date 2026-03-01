#!/bin/bash
# Check if cloudflared (Cloudflare Tunnel) is running.
# Run: ./check_cloudflared.sh   or   bash check_cloudflared.sh

set -e

if command -v pgrep >/dev/null 2>&1; then
  if pgrep -x cloudflared >/dev/null 2>&1; then
    echo "cloudflared is running (PID: $(pgrep -x cloudflared))"
    exit 0
  fi
elif command -v ps >/dev/null 2>&1; then
  if ps -e -o comm= 2>/dev/null | grep -q '^cloudflared$'; then
    echo "cloudflared is running"
    exit 0
  fi
  # macOS / some systems: ps aux
  if ps aux 2>/dev/null | grep -v grep | grep -q cloudflared; then
    echo "cloudflared is running"
    exit 0
  fi
fi

echo "cloudflared is NOT running"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ -x "$SCRIPT_DIR/bin/cloudflared" ]; then
  echo "Start it with: $SCRIPT_DIR/bin/cloudflared tunnel run <YOUR_TUNNEL_NAME>"
else
  echo "Start it with: cloudflared tunnel run <YOUR_TUNNEL_NAME>"
fi
echo "Or check: https://one.dash.cloudflare.com -> Networks -> Tunnels"
exit 1
