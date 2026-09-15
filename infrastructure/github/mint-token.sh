#!/usr/bin/env bash
# Mint a GitHub App installation token for a crew role. This is the operation the launcher's credential
# helper performs on demand; a token lives one hour and is never stored. Reads the App's private key from
# the host-local secret file and prints only the token to stdout.
# Usage: mint-token.sh <role>            e.g. mint-token.sh parker
set -euo pipefail
role="${1:?usage: mint-token.sh <role>}"
# Two layouts, because two situations. On the Spark each ROLE HAS ITS OWN UNIX ACCOUNT, so its one
# key sits flat in its own 700 directory and no sibling can read it. On the Mac a single account
# holds every role's key, so they are separated by subdirectory instead.
SECRETS="${NOSTROMO_SECRETS:-$HOME/.config/nostromo/secrets}"
if [[ -s "$SECRETS/github-app.pem" ]]; then
  pem="$SECRETS/github-app.pem"          # per-role account: the account is the role
else
  pem="$SECRETS/$role/github-app.pem"    # shared account: role as subdirectory
fi
[[ -s "$pem" ]] || { echo "no App private key at $pem" >&2; exit 1; }

# App and installation ids come from the crew manifest, which WP-1 recorded. The environment still
# overrides, for probing an App before it is in the manifest.
MANIFEST="${NOSTROMO_MANIFEST:-$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)/crew/manifest.yaml}"
if [[ -n "${GITHUB_APP_ID:-}" && -n "${GITHUB_APP_INSTALLATION_ID:-}" ]]; then
  app_id="$GITHUB_APP_ID"
  install_id="$GITHUB_APP_INSTALLATION_ID"
else
  [[ -r "$MANIFEST" ]] || { echo "no manifest at $MANIFEST and no GITHUB_APP_ID in the environment" >&2; exit 1; }
  ids=$(python3 -c '
import sys, yaml
manifest, role = sys.argv[1], sys.argv[2]
gh = ((yaml.safe_load(open(manifest)) or {}).get("agents", {}).get(role) or {}).get("github")
if not gh:
    sys.exit(f"{role} has no github section in {manifest}; register the App first")
print(gh["app_id"], gh["installation_id"])
' "$MANIFEST" "$role") || exit 1
  read -r app_id install_id <<<"$ids"
fi

b64url() { openssl base64 -A | tr '+/' '-_' | tr -d '='; }
now=$(date +%s)
header=$(printf '{"alg":"RS256","typ":"JWT"}' | b64url)
payload=$(printf '{"iat":%d,"exp":%d,"iss":"%s"}' "$((now - 60))" "$((now + 540))" "$app_id" | b64url)
sig=$(printf '%s.%s' "$header" "$payload" | openssl dgst -sha256 -sign "$pem" -binary | b64url)
jwt="$header.$payload.$sig"

curl -sS -X POST "https://api.github.com/app/installations/${install_id}/access_tokens" \
  -H "Authorization: Bearer $jwt" -H "Accept: application/vnd.github+json" \
  | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["token"]) if "token" in d else (sys.stderr.write(json.dumps(d)+"\n"), sys.exit(1))'
