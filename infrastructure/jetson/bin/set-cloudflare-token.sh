#!/usr/bin/env bash
# Install the Cloudflare DNS token on the Jetson, without it ever appearing in a terminal, a shell
# history, a transcript, or this repository.
#
# WHY THIS IS NOT THE GITHUB PATTERN. A GitHub App private key mints one-hour tokens on demand, so
# the durable secret never lives where it is used. Cloudflare has no such exchange: this token IS
# the credential and Caddy needs it resident to renew the certificate every ~60 days. It cannot be
# made short-lived, so it is made narrow, host-local, and loudly verifiable instead.
#
# Run from the Mac:  infrastructure/jetson/bin/set-cloudflare-token.sh [ssh-host]
set -euo pipefail
HOST="${1:-nano}"
ZONE="${CLOUDFLARE_ZONE:-backspring.xyz}"
REMOTE=/mnt/ssd/buzz/deploy/secrets.env
API=https://api.cloudflare.com/client/v4

# read -s: no echo, and because this is a script argument-free prompt, no shell history either.
read -rsp "Cloudflare API token (input hidden): " TOKEN
echo
[[ -n "$TOKEN" ]] || { echo "no token entered" >&2; exit 1; }

auth=(-H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json")
jqf() { python3 -c 'import sys,json;d=json.load(sys.stdin);print(eval(sys.argv[1],{"d":d}))' "$1"; }

echo "==> verifying the token is live"
v=$(curl -sS "${auth[@]}" "$API/user/tokens/verify")
echo "$v" | grep -q '"success":true' || { echo "token rejected by Cloudflare:"; echo "$v" | head -3; exit 1; }
token_id=$(echo "$v" | jqf 'd["result"]["id"]')
echo "    valid. token id $token_id  (record this — it is how you revoke exactly this token)"

echo "==> checking what it can reach"
zones=$(curl -sS "${auth[@]}" "$API/zones")
names=$(echo "$zones" | jqf '[z["name"] for z in d["result"]]')
echo "    zones visible: $names"
case "$names" in
  "['$ZONE']") echo "    PASS  scoped to $ZONE alone" ;;
  *) echo "    FAIL  expected exactly ['$ZONE'] — re-create the token scoped to one zone" >&2; exit 1 ;;
esac

echo "==> paired control: it must NOT be able to act outside DNS"
code=$(curl -sS -o /dev/null -w '%{http_code}' "${auth[@]}" "$API/user")
if [[ "$code" == "403" ]]; then
  echo "    PASS  /user refused ($code) — the token carries no account or user scope"
else
  echo "    FAIL  /user returned $code; expected 403. The token is broader than DNS edit." >&2
  exit 1
fi

echo "==> installing on $HOST (mode 600, never printed)"
# Replace-or-append, so re-running rotates rather than duplicating.
printf '%s' "$TOKEN" | ssh "$HOST" "
  umask 077
  touch $REMOTE
  grep -v '^CLOUDFLARE_API_TOKEN=' $REMOTE > $REMOTE.new || true
  printf 'CLOUDFLARE_API_TOKEN=%s\n' \"\$(cat)\" >> $REMOTE.new
  mv $REMOTE.new $REMOTE
  chmod 600 $REMOTE
  echo \"    written; secrets.env is now \$(wc -l < $REMOTE) lines, mode \$(stat -c %a $REMOTE)\"
"
unset TOKEN
echo "==> done. The token was not echoed, not logged, and is not in this repository."
echo "    Record token id $token_id in the WP-2 evidence so it can be revoked precisely."
