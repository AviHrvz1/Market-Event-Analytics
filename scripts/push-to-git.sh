#!/usr/bin/env bash
# Push current branch to origin. Usage: ./scripts/push-to-git.sh ["optional commit message"]
set -e
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if ! git remote get-url origin &>/dev/null; then
  echo "No remote 'origin' found. Add it with:"
  echo "  git remote add origin https://github.com/AviHrvz1/Market-Event-Analytics.git"
  exit 1
fi

MSG="${1:-Update: deploy to Beanstalk}"
git add .
git status --short
if ! git commit -m "$MSG"; then
  echo "Nothing to commit (or commit failed). Pushing existing commits..."
fi
BRANCH="$(git branch --show-current)"
git push origin "$BRANCH"
echo "Pushed to origin/$BRANCH"
