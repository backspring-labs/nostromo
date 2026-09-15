#!/usr/bin/env bash
# Mirror the Nostromo repo to the Spark (Bootstrap Plan §11.2).
#
# Driven from the Mac, like the Jetson. Deploy keys are disabled organization-wide on
# backspring-labs — a posture worth keeping — and no crew account holds a GitHub credential, so the
# repo is pushed here rather than cloned there.
#
# It lives under /opt/nostromo, NOT in a home directory: the manifest, personas and launch config
# are configuration that EVERY role must read, and role homes are 700. Nothing secret is in it.
#
# Usage: push-repo.sh [ssh-target]     default: nostromo@spark (the supervisor owns /opt/nostromo)
set -euo pipefail
TARGET="${1:-nostromo@spark}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

# This mirrors COMMITTED work. Uncommitted edits silently do not travel, and the far side then runs
# yesterday's script with today's arguments — which has now wasted two round trips.
if ! git diff --quiet || ! git diff --cached --quiet; then
  echo "uncommitted changes — commit first, or they will not reach the Spark:" >&2
  git status --short >&2
  exit 1
fi
BARE=/opt/nostromo/nostromo.git
WORK=/opt/nostromo/nostromo

ssh "$TARGET" "test -d $BARE || { git init --quiet --bare $BARE && \
  git --git-dir=$BARE symbolic-ref HEAD refs/heads/main; }"
git push --quiet "$TARGET:$BARE" "$BRANCH:$BRANCH"
ssh "$TARGET" "test -d $WORK || git clone --quiet $BARE $WORK
cd $WORK && git fetch --quiet origin && git checkout --quiet $BRANCH && \
  git reset --quiet --hard origin/\$BRANCH && \
  find $WORK -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; \
  chmod -R a+rX,go-w $WORK && \
  echo \"nostromo on \$(hostname) at \$(git log --oneline -1)\""
