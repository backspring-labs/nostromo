#!/usr/bin/env bash
# Git credential helper for a Nostromo crew role (NOSTROMO-PLAN-0001 §11.6).
#
# Mints a GitHub App installation token on demand and hands it to git. The token lives an hour and
# is never written to disk, so there is no long-lived credential in the crew account for an agent
# to find, and no credential at all for a role whose App does not exist yet.
#
# Wire it into a worktree, which binds the credential to the role rather than to the account:
#   git config --worktree credential.https://github.com.helper \
#     "!/path/to/credential-helper.sh parker"
#
# Usage: credential-helper.sh <role> <get|store|erase>
set -euo pipefail
role="${1:?usage: credential-helper.sh <role> <operation>}"
op="${2:-get}"

# store and erase are no-ops by design: there is nothing to persist and nothing to forget.
[[ "$op" == "get" ]] || exit 0

# git writes the request on stdin as key=value lines. Answer only for github.com.
host=""
while IFS='=' read -r key value; do
  [[ -z "$key" ]] && break
  [[ "$key" == "host" ]] && host="$value"
done
[[ "$host" == "github.com" ]] || exit 0

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
token="$("$HERE/mint-token.sh" "$role")" || {
  echo "could not mint a token for $role; is the App registered and the key present?" >&2
  exit 1
}

printf 'username=x-access-token\npassword=%s\n' "$token"
