#!/usr/bin/env bash
# Mirror the Nostromo repo to the Spark (NOSTROMO-PLAN-0001 §11.2).
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
BARE=/opt/nostromo/nostromo.git
WORK=/opt/nostromo/nostromo

ssh "$TARGET" "test -d $BARE || { git init --quiet --bare $BARE && \
  git --git-dir=$BARE symbolic-ref HEAD refs/heads/main; }"
git push --quiet "$TARGET:$BARE" "$BRANCH:$BRANCH"
ssh "$TARGET" "test -d $WORK || git clone --quiet $BARE $WORK
cd $WORK && git fetch --quiet origin && git checkout --quiet $BRANCH && \
  git reset --quiet --hard origin/$BRANCH && chmod -R a+rX $WORK && \
  echo \"nostromo on \$(hostname) at \$(git log --oneline -1)\""
