#!/usr/bin/env bash
# Deploy current directory to AWS Elastic Beanstalk. Run from repo root or scripts/.
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! command -v eb &>/dev/null; then
  echo "EB CLI not found. Install with: pip install awsebcli"
  echo "Then run 'eb init' once (see DEPLOY.md)."
  exit 1
fi

echo "Deploying from $REPO_ROOT..."
eb status 2>/dev/null || true
eb deploy
echo "Done. Run 'eb status' or 'eb open' for the environment URL."
