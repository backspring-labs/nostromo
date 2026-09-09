#!/usr/bin/env bash
# WP-2 health and boundary probes, run from the Mac (NOSTROMO-PLAN-0001 §9.8). Prints evidence, never secrets.
# Usage: infrastructure/jetson/bin/probe.sh [ssh-host]   (default: nano; SPARK_HOST overrides the Spark alias)
set -uo pipefail
HOST="${1:-nano}"
SPARK="${SPARK_HOST:-spark}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
eval "$(grep -E '^(BUZZ_DOMAIN|BUZZ_HTTP_PORT|BUZZ_BIND_IP)=' "$HERE/buzz/buzz.env")"
URL="http://${BUZZ_DOMAIN}:${BUZZ_HTTP_PORT}"
fail=0
check() {
  local name="$1"; shift
  local out
  if out=$("$@" 2>&1); then echo "PASS  ${name}: ${out:0:160}"; else echo "FAIL  ${name}: ${out:0:160}"; fail=1; fi
}

echo "== on ${HOST}"
check "liveness"        ssh "$HOST" 'curl -fsS http://127.0.0.1:8080/_liveness'
check "readiness"       ssh "$HOST" 'curl -fsS http://127.0.0.1:8080/_readiness'
check "containers"      ssh "$HOST" '/mnt/ssd/buzz/deploy/buzzctl status --format "table {{.Name}}\t{{.Status}}" | tail -n +2 | tr "\n" ";"'
check "volumes on NVMe" ssh "$HOST" 'for v in $(docker volume ls -q --filter label=com.buzz.volume); do m=$(docker volume inspect -f "{{.Mountpoint}}" "$v"); case "$m" in /mnt/ssd/*) printf "%s " "$v";; *) echo "NOT on NVMe: $v $m"; exit 1;; esac; done'
check "migrations"      ssh "$HOST" 'c=$(docker ps -q --filter label=com.docker.compose.service=relay); docker logs "$c" 2>&1 | grep -i -m1 migrat'
check "secrets mode"    ssh "$HOST" 'stat -c "%a %U" /mnt/ssd/buzz/deploy/secrets.env | grep -q "^600 " && echo 600'

echo "== from the Mac over the tailnet"
check "NIP-11 relay info"     curl -fsS -H 'Accept: application/nostr+json' "${URL}/"
check "well-known nostr.json" curl -fsS "${URL}/.well-known/nostr.json?name=probe"

echo "== from ${SPARK} over the tailnet"
check "spark NIP-11" ssh "$SPARK" "curl -fsS -H 'Accept: application/nostr+json' '${URL}/'"

echo "== boundary: LAN address must refuse"
LAN=$(ssh "$HOST" "ip -4 -o addr show scope global | awk '!/tailscale/{print \$4}' | cut -d/ -f1 | head -1")
if curl -sS -m 4 -o /dev/null "http://${LAN}:${BUZZ_HTTP_PORT}/" 2>/dev/null; then
  echo "FAIL  LAN ${LAN}:${BUZZ_HTTP_PORT} answered"; fail=1
else
  echo "PASS  LAN ${LAN}:${BUZZ_HTTP_PORT} refused"
fi
exit "$fail"
