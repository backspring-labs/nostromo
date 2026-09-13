#!/usr/bin/env bash
# Mirror the Nostromo repo to the Spark's crew account (NOSTROMO-PLAN-0001 §11.2).
#
# Driven from the Mac, like the Jetson. Deploy keys are disabled organization-wide on
# backspring-labs — a posture worth keeping — and the crew account deliberately holds no GitHub
# credential, so the repo is pushed here rather than cloned there. The crew account therefore has
# the manifests, personas and launch configuration it needs, and no way to reach GitHub with them.
#
# Usage: push-repo.sh [ssh-target]     default: nostromo@spark
set -euo pipefail
TARGET="${1:-nostromo@spark}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

ssh "$TARGET" 'test -d $HOME/nostromo.git || { git init --quiet --bare $HOME/nostromo.git && \
  git --git-dir=$HOME/nostromo.git symbolic-ref HEAD refs/heads/main; }'
git push --quiet "$TARGET:nostromo.git" "$BRANCH:$BRANCH"
ssh "$TARGET" "test -d \$HOME/nostromo || git clone --quiet \$HOME/nostromo.git \$HOME/nostromo
cd \$HOME/nostromo && git fetch --quiet origin && git checkout --quiet $BRANCH && \
  git reset --quiet --hard origin/$BRANCH && \
  echo \"nostromo on \$(hostname) at \$(git log --oneline -1)\""
