#!/usr/bin/env bash
# Push to Git then deploy to Beanstalk. Usage: ./scripts/push-and-deploy.sh ["optional commit message"]
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/push-to-git.sh" "$@"
"$SCRIPT_DIR/deploy-to-beanstalk.sh"
