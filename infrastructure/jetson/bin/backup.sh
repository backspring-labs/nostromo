#!/usr/bin/env bash
# Runs ON the Jetson. Minimum recovery copy (Bootstrap Plan §9.9): secrets, Postgres dump, git/media/redis
# volumes, and the config that produced them. Output: /mnt/ssd/buzz/backups/<UTC stamp>/ (mode 700).
# Keeps the newest $KEEP sets. Copy the newest set off-host afterwards; a same-disk copy is not disaster recovery.
set -euo pipefail
DEPLOY=/mnt/ssd/buzz/deploy
ROOT=/mnt/ssd/buzz/backups
KEEP="${KEEP:-7}"
cd "$DEPLOY"
umask 077
compose() {
  docker compose --env-file buzz.env --env-file secrets.env -f compose.yml -f compose.nostromo.yml "$@"
}
eval "$(grep -E '^(POSTGRES_USER|POSTGRES_DB)=' buzz.env)"
TAR_IMAGE=$(grep -oE 'postgres:17-alpine@sha256:[0-9a-f]{64}' compose.nostromo.yml | head -1)

STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT="$ROOT/$STAMP"
mkdir -p "$OUT"
trap 'echo "backup failed; removing incomplete set $OUT" >&2; rm -rf "$OUT"' ERR
cp secrets.env buzz.env upstream.lock "$OUT/"
[[ -f relay.pubkey ]] && cp relay.pubkey "$OUT/"

compose exec -T postgres pg_dump -U "${POSTGRES_USER:-buzz}" -d "${POSTGRES_DB:-buzz}" -Fc > "$OUT/postgres.dump"
for v in git minio redis; do
  vol=$(docker volume ls -q --filter "label=com.buzz.volume=$v")
  [[ -n "$vol" ]] || { echo "no volume labelled com.buzz.volume=$v" >&2; exit 1; }
  # Runs as root inside the container so every file in the volume is readable; hands the archive back to us.
  docker run --rm --entrypoint sh -v "$vol:/src:ro" -v "$OUT:/out" "$TAR_IMAGE" \
    -c "tar -C /src -czf /out/$v.tgz . && chown $(id -u):$(id -g) /out/$v.tgz && chmod 600 /out/$v.tgz"
done
(cd "$OUT" && sha256sum ./* > SHA256SUMS)
chmod 600 "$OUT"/*
du -sh "$OUT"
# Prune to the newest $KEEP sets.
ls -1dt "$ROOT"/*/ | tail -n +$((KEEP + 1)) | xargs -r rm -rf
echo "backup: $OUT"
