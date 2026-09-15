#!/usr/bin/env bash
# WP-2 health and boundary probes, run from the Mac (Bootstrap Plan §9.8). Prints evidence, never secrets.
# Usage: infrastructure/jetson/bin/probe.sh [ssh-host]   (default: nano; SPARK_HOST overrides the Spark alias)
set -uo pipefail
HOST="${1:-nano}"
SPARK="${SPARK_HOST:-spark}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
eval "$(grep -E '^(BUZZ_DOMAIN|BUZZ_HTTP_PORT)=' "$HERE/buzz/buzz.env")"
URL="https://${BUZZ_DOMAIN}"
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

# The Cloudflare token is long-lived by necessity and is used once every ~60 days, at renewal. A
# revoked or expired token is therefore invisible until the certificate is already failing to
# renew, and then for up to 30 more days until it actually expires. Checking it on every probe
# turns a silent, delayed failure into a loud, immediate one. Skipped, not failed, before the
# token exists. The token is read on the Jetson and never leaves it.
if ssh "$HOST" 'grep -q "^CLOUDFLARE_API_TOKEN=..*" /mnt/ssd/buzz/deploy/secrets.env' 2>/dev/null; then
  check "cloudflare token valid" ssh "$HOST" '
    t=$(grep "^CLOUDFLARE_API_TOKEN=" /mnt/ssd/buzz/deploy/secrets.env | cut -d= -f2-)
    r=$(curl -sS -H "Authorization: Bearer $t" https://api.cloudflare.com/client/v4/user/tokens/verify)
    echo "$r" | grep -q "\"status\":\"active\"" || { echo "token not active: $(echo "$r" | head -c 120)"; exit 1; }
    echo "active, id $(echo "$r" | sed -n "s/.*\"id\":\"\([a-f0-9]*\)\".*/\1/p" | head -1)"'
else
  echo "SKIP  cloudflare token valid: not installed yet (bin/set-cloudflare-token.sh)"
fi

# Tailscale Serve was replaced by Caddy on 2026-09-13: Serve cannot issue for a name outside the
# tailnet, and the relay's hostname has to outlive the tailnet because every agent handle carries
# it. What still matters is unchanged — 443 reachable only on the tailnet address, and Funnel off.
check "443 on tailnet addr only" ssh "$HOST" 'ss -tln | awk "\$4 ~ /:443\$/ {print \$4}" | grep -qx "$(tailscale ip -4):443" && echo "bound to $(tailscale ip -4):443 only"'
check "funnel off"               ssh "$HOST" '! tailscale funnel status 2>&1 | grep -qiE "^https|proxy" && echo "no funnel"'

echo "== from the Mac over the tailnet, TLS via Caddy"
check "certificate"           bash -c "echo | openssl s_client -connect ${BUZZ_DOMAIN}:443 -servername ${BUZZ_DOMAIN} 2>/dev/null | openssl x509 -noout -issuer -enddate | tr '\n' ' '"
check "NIP-11 relay info"     curl -fsS -H 'Accept: application/nostr+json' "${URL}/"
check "well-known nostr.json" curl -fsS "${URL}/.well-known/nostr.json?name=probe"
check "wss upgrade 101"       bash -c "curl -sS -i -m 5 --http1.1 -H 'Connection: Upgrade' -H 'Upgrade: websocket' -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' '${URL}/' 2>/dev/null | head -1 | grep ' 101 '"

echo "== from ${SPARK} over the tailnet"
check "spark NIP-11" ssh "$SPARK" "curl -fsS -H 'Accept: application/nostr+json' '${URL}/'"

echo "== boundary: plaintext port closed to the tailnet, LAN address refuses"
TSIP=$(ssh "$HOST" "tailscale ip -4")
LAN=$(ssh "$HOST" "ip -4 -o addr show scope global | awk '!/tailscale/{print \$4}' | cut -d/ -f1 | head -1")
refuse() {
  local name="$1" url="$2"
  if curl -sS -k -m 4 -o /dev/null "$url" 2>/dev/null; then echo "FAIL  ${name} answered: ${url}"; fail=1; else echo "PASS  ${name} refused: ${url}"; fi
}
refuse "tailnet plaintext" "http://${TSIP}:${BUZZ_HTTP_PORT}/"
refuse "LAN plaintext"     "http://${LAN}:${BUZZ_HTTP_PORT}/"
refuse "LAN https"         "https://${LAN}/"
exit "$fail"
