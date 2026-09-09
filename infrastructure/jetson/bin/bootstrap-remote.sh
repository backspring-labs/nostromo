#!/usr/bin/env bash
# Runs ON the Jetson, invoked by install.sh after the deploy directory is synced.
# First run: generates host-local secrets (never leaves the host except via backup.sh). Every run: pull + start.
set -euo pipefail
DEPLOY=/mnt/ssd/buzz/deploy
cd "$DEPLOY"
umask 077
# shellcheck disable=SC1091
source ./upstream.lock
IMAGE="ghcr.io/block/buzz@${BUZZ_IMAGE_INDEX_DIGEST}"

if [[ ! -f secrets.env ]]; then
  echo "==> generating host-local secrets (first run only)"
  docker pull -q "$IMAGE" >/dev/null
  keys=$(docker run --rm --entrypoint /usr/local/bin/buzz-admin "$IMAGE" generate-key)
  relay_pub=$(awk '/^Public key:/{print $3}' <<<"$keys")
  relay_sec=$(awk '/^Secret key:/{print $3}' <<<"$keys")
  [[ ${#relay_pub} -eq 64 && ${#relay_sec} -eq 64 ]] || { echo "unexpected buzz-admin generate-key output" >&2; exit 1; }
  {
    echo "# Generated on $(hostname) at $(date -u +%FT%TZ) by bootstrap-remote.sh. Never commit. Back up with backup.sh."
    echo "BUZZ_RELAY_PRIVATE_KEY=$relay_sec"
    echo "BUZZ_GIT_HOOK_HMAC_SECRET=$(openssl rand -hex 32)"
    echo "POSTGRES_PASSWORD=$(openssl rand -hex 24)"
    echo "REDIS_PASSWORD=$(openssl rand -hex 24)"
    echo "BUZZ_S3_ACCESS_KEY=$(openssl rand -hex 10)"
    echo "BUZZ_S3_SECRET_KEY=$(openssl rand -hex 20)"
  } > secrets.env
  chmod 600 secrets.env
  echo "$relay_pub" > relay.pubkey
  echo "relay public key: $relay_pub"
fi

# Every key the template names must be present with a real value; a stale template-shaped file must not start.
while read -r key; do
  if ! grep -qE "^${key}=.+" secrets.env || grep -qE "^${key}=.*CHANGE_ME" secrets.env; then
    echo "secrets.env is missing a real value for ${key}" >&2
    exit 1
  fi
done < <(grep -oE '^[A-Z0-9_]+' secrets.env.template)

echo "==> pulling pinned images"
./buzzctl pull
echo "==> starting the stack"
./buzzctl start
./buzzctl status
