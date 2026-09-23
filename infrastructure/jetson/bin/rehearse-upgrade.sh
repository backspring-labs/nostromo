#!/usr/bin/env bash
# Rehearse a relay upgrade on the Mac against a real backup set, before the Jetson sees it.
#
# It is two tests at once:
#   1. A restore test. A backup nobody has restored is a hope. The set's pg_dump goes into the same
#      pinned Postgres the Jetson runs, and the OLD relay's migrator must accept the result.
#   2. The migration, measured rather than read. The NEW image migrates the restored copy — timed,
#      with row counts compared before and after — and then the old image is asked to migrate again.
#      If it refuses, rolling back needs this backup, and the output says so instead of a README.
#
# Nothing here touches the Jetson. The restored database is production data, so it lives only in a
# throwaway container with no published port, removed on exit.
#
# Usage: rehearse-upgrade.sh <backup-dir>
#   old image = the set's own upstream.lock (what produced the dump); new = the repo's upstream.lock
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BK="${1:?usage: rehearse-upgrade.sh <backup-dir>}"
BK="${BK%/}"
die() { echo "rehearse: $*" >&2; exit 1; }
say() { echo "== $*"; }
now() { python3 -c 'import time; print(time.time())'; }

[[ -f "$BK/postgres.dump" && -f "$BK/upstream.lock" && -f "$BK/SHA256SUMS" ]] || die "$BK is not a backup set"
(cd "$BK" && shasum -a 256 -c --quiet SHA256SUMS) || die "$BK fails its own checksums"
docker info >/dev/null 2>&1 || die "Docker is not running"
lockval() { (source "$1" && eval "echo \$$2"); }
OLD="$(lockval "$BK/upstream.lock" BUZZ_IMAGE_INDEX_DIGEST)";   OLD_C="$(lockval "$BK/upstream.lock" BUZZ_COMMIT)"
NEW="$(lockval "$HERE/buzz/upstream.lock" BUZZ_IMAGE_INDEX_DIGEST)"; NEW_C="$(lockval "$HERE/buzz/upstream.lock" BUZZ_COMMIT)"
PG_IMAGE="$(grep -oE 'postgres:17-alpine@sha256:[0-9a-f]{64}' "$HERE/buzz/compose.nostromo.yml" | head -1)"
[[ -n "$PG_IMAGE" ]] || die "no pinned Postgres image in compose.nostromo.yml"
say "backup $(basename "$BK"): old ${OLD_C:0:10} -> new ${NEW_C:0:10}"
[[ "$OLD" != "$NEW" ]] || echo "   same image on both sides: this is a restore test only"

N="nostromo-rehearsal-$$"
cleanup() { docker rm -f -v "$N-pg" >/dev/null 2>&1 || true; docker network rm "$N" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker network create "$N" >/dev/null
docker run -d --name "$N-pg" --network "$N" -e POSTGRES_USER=buzz -e POSTGRES_DB=buzz \
  -e POSTGRES_PASSWORD=rehearsal "$PG_IMAGE" >/dev/null
# Probe over TCP, not the socket: the image's entrypoint first runs a socket-only server to create
# the database, and pg_isready answers yes to that one before the database exists.
for _ in $(seq 1 60); do docker exec "$N-pg" pg_isready -h 127.0.0.1 -U buzz -d buzz -q 2>/dev/null && break; sleep 1; done
docker exec "$N-pg" pg_isready -h 127.0.0.1 -U buzz -d buzz -q || die "Postgres did not come up"

sql() { docker exec -i "$N-pg" psql -U buzz -d buzz -qAtX -v ON_ERROR_STOP=1 -c "$1"; }
admin() {  # image-digest -> runs buzz-admin migrate against the throwaway copy
  docker run --rm --network "$N" -e DATABASE_URL="postgres://buzz:rehearsal@$N-pg:5432/buzz" \
    --entrypoint /usr/local/bin/buzz-admin "ghcr.io/block/buzz@$1" migrate
}
# Durable state an upgrade must not lose. Schema version is reported separately because it is
# supposed to change.
DATA_SQL="select concat_ws(' ',
  'events=' || (select count(*) from events), 'channels=' || (select count(*) from channels),
  'members=' || (select count(*) from relay_members), 'audit=' || (select count(*) from audit_log))"
VERSION_SQL="select max(version) from _sqlx_migrations where success"

say "restore test"
docker exec -i "$N-pg" pg_restore -U buzz -d buzz --exit-on-error < "$BK/postgres.dump" || die "pg_restore failed"
BEFORE="$(sql "$DATA_SQL")"
echo "   restored: schema $(sql "$VERSION_SQL"), $BEFORE"
admin "$OLD" >/dev/null 2>&1 || die "the OLD relay (${OLD_C:0:10}) will not accept its own restored backup — the backup is not restorable"
echo "   ok: the old relay accepts the restored copy, so this set is a working rollback point"

if [[ "$OLD" == "$NEW" ]]; then say "done: restore test passed"; exit 0; fi

say "migrating with the new image"
t0="$(now)"
out="$(admin "$NEW" 2>&1)" || die "the NEW image failed to migrate the restored copy: $(echo "$out" | tail -3)"
t1="$(now)"
echo "   $(echo "$out" | tail -1)"
AFTER="$(sql "$DATA_SQL")"
echo "   schema now $(sql "$VERSION_SQL"), took $(python3 -c "print(f'{$t1 - $t0:.1f}s')") including container start"
[[ "$AFTER" == "$BEFORE" ]] || die "row counts changed across the migration: before '$BEFORE', after '$AFTER'"
echo "   ok: $AFTER unchanged"
if [[ "$(sql "select count(*) from information_schema.columns where table_name='audit_log' and column_name='hash_version'")" == 1 ]]; then
  echo "   audit_log by hash_version: $(sql "select coalesce(string_agg('v' || hash_version || '=' || n, ' '), 'empty') from (select hash_version, count(*) n from audit_log group by 1 order by 1) s")"
fi

say "can the old relay start on the migrated schema?"
if out="$(admin "$OLD" 2>&1)"; then
  echo "   yes: rolling back is possible without restoring this backup"
else
  echo "   no — $(echo "$out" | grep -iE 'error|missing|migrat' | tail -1 | cut -c1-160)"
  echo "   rollback therefore means: old pin + restore $(basename "$BK"). Anything written after the upgrade is lost."
fi
say "rehearsal passed"
