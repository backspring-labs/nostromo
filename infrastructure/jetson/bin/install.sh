#!/usr/bin/env bash
# Install or update the Buzz relay on the Jetson from the owner's Mac (NOSTROMO-PLAN-0001 WP-2).
# Idempotent: every run re-syncs the repo-managed files and restarts the stack; host-generated secrets are never
# touched. The Nostromo repo is never cloned on the Jetson, and no GitHub credential is placed there.
# Usage: infrastructure/jetson/bin/install.sh [ssh-host]   (default: nano)
set -euo pipefail
HOST="${1:-nano}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$HERE/buzz/upstream.lock"
REMOTE_ROOT=/mnt/ssd/buzz
# shellcheck disable=SC1090
source "$LOCK"

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

echo "==> fetching block/buzz deploy/compose/compose.yml at ${BUZZ_COMMIT}"
gh api "repos/block/buzz/contents/deploy/compose/compose.yml?ref=${BUZZ_COMMIT}" \
  -H "Accept: application/vnd.github.raw" > "$STAGE/compose.yml"
actual=$(shasum -a 256 "$STAGE/compose.yml" | awk '{print $1}')
if [[ "$actual" != "$SHA256_COMPOSE_YML" ]]; then
  echo "compose.yml sha256 $actual does not match upstream.lock ($SHA256_COMPOSE_YML); refusing to install" >&2
  exit 1
fi
grep -q "BUZZ_IMAGE=ghcr.io/block/buzz@${BUZZ_IMAGE_INDEX_DIGEST}" "$HERE/buzz/buzz.env" \
  || { echo "buzz.env BUZZ_IMAGE does not match upstream.lock" >&2; exit 1; }

cp "$HERE/buzz/compose.nostromo.yml" "$HERE/buzz/buzz.env" "$HERE/buzz/secrets.env.template" "$LOCK" "$STAGE/"
cp "$HERE/bin/buzzctl" "$HERE/bin/backup.sh" "$HERE/bin/bootstrap-remote.sh" "$STAGE/"
chmod 644 "$STAGE"/compose.yml "$STAGE"/compose.nostromo.yml "$STAGE"/buzz.env "$STAGE"/secrets.env.template "$STAGE"/upstream.lock
chmod 755 "$STAGE"/buzzctl "$STAGE"/backup.sh "$STAGE"/bootstrap-remote.sh

echo "==> syncing to ${HOST}:${REMOTE_ROOT}/deploy"
ssh "$HOST" "mkdir -p ${REMOTE_ROOT}/deploy ${REMOTE_ROOT}/backups && chmod 700 ${REMOTE_ROOT} ${REMOTE_ROOT}/deploy ${REMOTE_ROOT}/backups"
rsync -a "$STAGE/compose.yml" "$STAGE/compose.nostromo.yml" "$STAGE/buzz.env" \
  "$STAGE/secrets.env.template" "$STAGE/upstream.lock" "${HOST}:${REMOTE_ROOT}/deploy/"
rsync -a "$STAGE/buzzctl" "$STAGE/backup.sh" "$STAGE/bootstrap-remote.sh" "${HOST}:${REMOTE_ROOT}/deploy/"

echo "==> bootstrapping on ${HOST}"
ssh "$HOST" "${REMOTE_ROOT}/deploy/bootstrap-remote.sh"
