#!/usr/bin/env bash
# Mint a GitHub App installation token for a crew role. This is the operation the launcher's credential
# helper performs on demand; a token lives one hour and is never stored. Reads the App's private key from
# the host-local secret file and prints only the token to stdout.
# Usage: mint-token.sh <role>            e.g. mint-token.sh parker
set -euo pipefail
role="${1:?usage: mint-token.sh <role>}"
SECRETS="${NOSTROMO_SECRETS:-$HOME/.config/nostromo/secrets}"
pem="$SECRETS/$role/github-app.pem"
[[ -s "$pem" ]] || { echo "no App private key at $pem" >&2; exit 1; }

# App and installation ids come from the crew manifest's github section; passed in until WP-1 records them.
app_id="${GITHUB_APP_ID:?set GITHUB_APP_ID}"
install_id="${GITHUB_APP_INSTALLATION_ID:?set GITHUB_APP_INSTALLATION_ID}"

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
now=$(date +%s)
header=$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)
payload=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' "$((now - 60))" "$((now + 540))" "$app_id" | b64url)
sig=$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$pem" -binary | b64url)
jwt="$header.$payload.$sig"

curl -sS -X POST "https://api.github.com/app/installations/${install_id}/access_tokens" \
  -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["token"]) if "token" in d else (sys.stderr.write(json.dumps(d)+"\n"), sys.exit(1))'
