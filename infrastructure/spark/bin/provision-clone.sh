#!/usr/bin/env bash
# Give a role its own clone of squad-ops. Runs ON the Spark, AS that role.
#
# Not a git worktree. Worktrees hang off one bare repository and write metadata back into it, so
# four roles sharing one bare repo means four roles with write access to the same directory —
# the group-writable pattern already removed from the repo checkout, the log directories and the
# shared worktree root. A clone per role has no shared writable state at all: Brett's checkout is
# brett:brett 700 and Parker cannot see it, let alone change it.
#
# squad-ops is public, so cloning needs no credential. Only pushing does, and that uses the role's
# own GitHub App token minted on demand by mint-token.sh — never a stored one.
#
# Usage:  provision-clone.sh            (as the role)
set -euo pipefail

ROLE="$(id -un)"
REPO="${NOSTROMO_REPO:-/opt/nostromo/nostromo-src}"
MANIFEST="$REPO/crew/manifest.yaml"
UPSTREAM="${SQUADOPS_URL:-https://github.com/backspring-labs/squad-ops.git}"
DEST="${SQUADOPS_DEST:-$HOME/src/squad-ops}"

die() { echo "provision-clone: $*" >&2; exit 1; }
[[ -r "$MANIFEST" ]] || die "missing $MANIFEST — run push-repo.sh from the Mac"

yaml_agent() {  # yaml_agent <key>  — under agents: <ROLE>:
  awk -v r="$ROLE" -v k="$1" '
    /^agents:/ { ina = 1; next }
    ina && /^  [a-z]+:/ { role = $1; sub(":", "", role) }
    ina && role == r && $1 == k":" { print $2; exit }' "$MANIFEST"
}
yaml_github() {  # yaml_github <key>  — under agents: <ROLE>: github:
  awk -v r="$ROLE" -v k="$1" '
    /^agents:/ { ina = 1; next }
    ina && /^  [a-z]+:/ { role = $1; sub(":", "", role); ing = 0 }
    ina && role == r && $1 == "github:" { ing = 1; next }
    ing && $1 == k":" { print $2; exit }
    ing && /^    [a-z_]+:/ && $1 != k":" { next }' "$MANIFEST"
}

[[ -n "$(yaml_agent buzz_pubkey)" ]] || die "$ROLE is not an agent in the manifest"

BOT_LOGIN="$(yaml_github bot_login)"
BOT_UID="$(yaml_github bot_user_id)"
[[ -n "$BOT_LOGIN" && -n "$BOT_UID" ]] \
  || die "$ROLE has no github.bot_login / bot_user_id in the manifest — a commit would be attributed to nobody"

if [[ -d "$DEST/.git" ]]; then
  echo "provision-clone: $DEST already exists"
else
  install -d -m 700 "$(dirname "$DEST")"
  echo "provision-clone: cloning $UPSTREAM → $DEST"
  git clone --quiet "$UPSTREAM" "$DEST"
  chmod 700 "$DEST"
fi

cd "$DEST"
# Attribution is the point of per-role accounts, so the checkout must not be able to commit as
# anyone else. Repo-local config only: never touch the role's global git config.
git config user.name  "$BOT_LOGIN"
git config user.email "${BOT_UID}+${BOT_LOGIN}@users.noreply.github.com"
# No stored credential. mint-token.sh issues a short-lived App token at push time.
git config credential.helper ""

cat <<INFO

provision-clone: $ROLE
  path        $DEST  ($(stat -c '%U:%G %a' "$DEST"))
  origin      $(git remote get-url origin)
  branch      $(git rev-parse --abbrev-ref HEAD) @ $(git log --oneline -1)
  commits as  $(git config user.name) <$(git config user.email)>
  size        $(du -sh "$DEST" | cut -f1)

INFO
