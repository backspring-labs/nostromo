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
# Usage:  provision-clone.sh              (as the role)
#         provision-clone.sh --read-only  (as a role that never commits — Ash: no commit identity, no
#                                         push URL, no venv. Reading a public repository needs none.)
set -euo pipefail

ROLE="$(id -un)"
READ_ONLY=0; [[ "${1:-}" == "--read-only" ]] && READ_ONLY=1
REPO="${NOSTROMO_REPO:-/opt/nostromo/nostromo-src}"
MANIFEST="$REPO/crew/manifest.yaml"
UPSTREAM="${SQUADOPS_URL:-https://github.com/backspring-labs/squad-ops.git}"
DEST="${SQUADOPS_DEST:-$HOME/src/squad-ops}"

# uv lives in the Nostromo runtime, not on a login shell PATH.
source /opt/nostromo/runtime/env.sh

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
if [[ $READ_ONLY == 0 ]]; then
  [[ -n "$BOT_LOGIN" && -n "$BOT_UID" ]] \
    || die "$ROLE has no github.bot_login / bot_user_id in the manifest — a commit would be attributed to nobody (a role that only reads: --read-only)"
fi

if [[ -d "$DEST/.git" ]]; then
  echo "provision-clone: $DEST already exists"
else
  install -d -m 700 "$(dirname "$DEST")"
  echo "provision-clone: cloning $UPSTREAM → $DEST"
  git clone --quiet "$UPSTREAM" "$DEST"
  chmod 700 "$DEST"
fi

cd "$DEST"
if [[ $READ_ONLY == 1 ]]; then
  # A reader cannot commit or push by accident: with useConfigOnly and no identity, git refuses to
  # commit ("Please tell me who you are"), and the push URL is not a URL.
  git config --unset-all user.name 2>/dev/null || true
  git config --unset-all user.email 2>/dev/null || true
  git config user.useConfigOnly true
  git config remote.origin.pushurl "no-push://read-only-role"
  git config credential.helper ""
  echo "provision-clone: $DEST is read-only for $ROLE — fetch works; commit and push are refused"
  exit 0
fi
# Attribution is the point of per-role accounts, so the checkout must not be able to commit as
# anyone else. Repo-local config only: never touch the role's global git config.
git config user.name  "$BOT_LOGIN"
git config user.email "${BOT_UID}+${BOT_LOGIN}@users.noreply.github.com"
# No stored credential. mint-token.sh issues a short-lived App token at push time.
git config credential.helper ""

# A clone without tooling is a checkout the role cannot verify anything in — Brett's first lint
# run had to fall back to `uvx ruff` because no venv existed, which he correctly flagged as a
# provenance risk: an unpinned ruff is not the one CI runs.
if [[ "${NOSTROMO_SKIP_VENV:-}" == "" ]]; then
  if [[ ! -x .venv/bin/python ]]; then
    echo "provision-clone: creating .venv (python 3.12)"
    uv venv --python 3.12 --quiet .venv || die "venv creation failed"
  fi
  echo "provision-clone: installing the package and pinned test requirements"
  export VIRTUAL_ENV="$PWD/.venv"
  # Two installs, checked separately. `if ! A && B` only runs B when A succeeds, which is how an
  # earlier version of validate-worktrees.sh skipped the test requirements entirely and then
  # blamed the gate for not finding ruff.
  uv pip install --quiet -e . -c ci-constraints.txt || die "package install failed"
  uv pip install --quiet -r tests/requirements.txt -c ci-constraints.txt \
    || die "test requirements install failed"
  for tool in ruff pytest; do
    [[ -x ".venv/bin/$tool" ]] || die "$tool missing after install — the checkout cannot verify anything"
  done
fi

cat <<INFO

provision-clone: $ROLE
  path        $DEST  ($(stat -c '%U:%G %a' "$DEST"))
  origin      $(git remote get-url origin)
  branch      $(git rev-parse --abbrev-ref HEAD) @ $(git log --oneline -1)
  commits as  $(git config user.name) <$(git config user.email)>
  python      $([[ -x .venv/bin/python ]] && .venv/bin/python --version || echo "no venv")
  size        $(du -sh "$DEST" | cut -f1)

INFO
