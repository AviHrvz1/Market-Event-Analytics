#!/usr/bin/env bash
# Set Schwab OAuth callback URL on Elastic Beanstalk to the custom domain (Option B).
# This avoids Chrome's "Dangerous site" warning when returning from Schwab login.
# Run from repo root: ./scripts/set-schwab-callback-url.sh
# After running: add the same URL as Redirect URI in your Schwab developer app at
#   https://developer.schwab.com (or beta-developer.schwab.com).
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

CALLBACK_URL="${SCHWAB_TOS_CALLBACK_URL:-https://api.avi-marketdata.xyz/schwab/callback}"

if ! command -v eb &>/dev/null; then
  echo "EB CLI not found. Install with: pip install awsebcli"
  exit 1
fi

echo "Setting SCHWAB_TOS_CALLBACK_URL on Beanstalk to: $CALLBACK_URL"
eb setenv "SCHWAB_TOS_CALLBACK_URL=$CALLBACK_URL"
echo "Done. Beanstalk will use this URL for the Schwab OAuth redirect."
echo ""
echo "Next steps:"
echo "  1. In Schwab developer portal, set your app's Redirect URI to: $CALLBACK_URL"
echo "  2. Open the app via the custom domain (e.g. https://api.avi-marketdata.xyz) and use Schwab setup from there."
echo "  See DEPLOY.md section 'Schwab callback (Option B)' for details."
