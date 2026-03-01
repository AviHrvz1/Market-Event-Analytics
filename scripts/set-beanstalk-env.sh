#!/usr/bin/env bash
# Push environment variables from .env to Elastic Beanstalk.
# Run from repo root: ./scripts/set-beanstalk-env.sh
# Requires: .env file with keys, eb CLI, and current env target (e.g. layoff-tracker-prod).
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ ! -f .env ]; then
  echo "No .env file. Create one with PRIXE_API_KEY, SCHWAB_*, etc., or set variables in AWS Console."
  exit 1
fi

# Load .env (simple KEY=value; no export of arbitrary code)
set -a
# shellcheck source=/dev/null
source .env 2>/dev/null || true
set +a

# Build list of KEY=value for vars we care about (only if set)
VARS=()
for key in PRIXE_API_KEY SCHWAB_TOS_API_KEY SCHWAB_TOS_API_SECRET SCHWAB_TOS_REFRESH_TOKEN CLAUDE_API_KEY NEWS_API_KEY; do
  val="${!key:-}"
  [ -n "$val" ] && VARS+=( "$key=$val" )
done
# Callback URL: use custom domain on EB to avoid Chrome "Dangerous site" (Option B)
key=SCHWAB_TOS_CALLBACK_URL
val="${!key:-https://api.avi-marketdata.xyz/schwab/callback}"
[ -n "$val" ] && VARS+=( "$key=$val" )
# Optional
for key in SCHWAB_TOS_APP_MACHINE_NAME SCHWAB_HEARTBEAT_INTERVAL_HOURS MAX_ARTICLES_TO_PROCESS PRIXE_PRICE_ENDPOINT PRIXE_BASE_URL; do
  val="${!key:-}"
  [ -n "$val" ] && VARS+=( "$key=$val" )
done

if [ ${#VARS[@]} -eq 0 ]; then
  echo "No env vars found in .env for PRIXE/SCHWAB/CLAUDE/NEWS. Add them to .env and re-run."
  exit 1
fi

echo "Setting ${#VARS[@]} environment variable(s) on Beanstalk..."
eb setenv "${VARS[@]}"
echo "Done. Restart the app if needed: eb deploy (or wait for next deploy)."
