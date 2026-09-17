#!/usr/bin/env bash
# Talk to a crew role directly in a terminal — no Buzz, no relay, no identity.
#
# For evaluating a role's configuration by hand: same account, same model, same persona, same
# clone and the same uid boundary, but nothing connected to the crew. Use it under Herdr so the
# session survives your laptop closing.
#
# Deliberately does NOT export BUZZ_PRIVATE_KEY. Without it the `buzz` CLI cannot publish, so this
# session is physically incapable of speaking as the crew member — no duplicate answers in
# #nostromo, no events signed by an identity that systemd is also running. One identity, one
# process, enforced by omission rather than by remembering.
#
# Goose rather than buzz-agent because buzz-agent is a stdio JSON-RPC server with no interactive
# mode. This is not the harness the role runs in production, which is the point: it is a bench.
#
# Usage:  talk-to.sh [--model <ollama-tag>] [--persona <file>]     (as the role, on the Spark)
set -euo pipefail

ROLE="$(id -un)"
REPO="${NOSTROMO_REPO:-/opt/nostromo/nostromo-src}"
MANIFEST="$REPO/crew/manifest.yaml"

die() { echo "talk-to: $*" >&2; exit 1; }
source /opt/nostromo/runtime/env.sh
[[ -r "$MANIFEST" ]] || die "missing $MANIFEST"
command -v goose >/dev/null || die "goose is not installed on this host"

yaml_agent() {
  awk -v r="$ROLE" -v k="$1" '
    /^agents:/ { ina = 1; next }
    ina && /^  [a-z]+:/ { role = $1; sub(":", "", role) }
    ina && role == r && $1 == k":" { print $2; exit }' "$MANIFEST"
}

MODEL=""; PERSONA="$REPO/crew/personas/$ROLE.md"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --model)   MODEL="$2"; shift 2 ;;
    --persona) PERSONA="$2"; shift 2 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[[ -n "$MODEL" ]] || MODEL="$(yaml_agent ollama_tag)"
[[ -n "$MODEL" ]] || die "no ollama_tag for $ROLE in the manifest and no --model given"
[[ -r "$PERSONA" ]] || die "no persona at $PERSONA"

# Where the role actually works, so relative paths behave as they do in production.
WORKDIR="$HOME/src/squad-ops"; [[ -d "$WORKDIR" ]] || WORKDIR="$HOME"

# The persona tells the role to answer by running `buzz messages send`. That is true in the crew
# and false here, and an instruction the session cannot follow is worse than none — it produced
# four hours of silent turns when it was accidentally true. Override it explicitly.
SYSTEM="$(cat "$PERSONA")

---

SESSION CONTEXT: this is a direct terminal session, not Buzz. There is no channel, no relay, and
no crew. Ignore every instruction above about publishing with \`buzz messages send\` — reply in
plain text to the person typing. Everything else about your role still applies: what you own, what
you refuse, and how you report evidence."

cat <<INFO
talk-to: $ROLE  (direct session — NOT the crew)
  model      $MODEL via local Ollama
  persona    $PERSONA
  workdir    $WORKDIR
  buzz       disabled (no private key in this environment)
  note       the crew's $ROLE keeps running under systemd; this session cannot speak as it

INFO

cd "$WORKDIR"
export GOOSE_PROVIDER=ollama GOOSE_MODEL="$MODEL" OLLAMA_HOST=http://localhost:11434 GOOSE_MODE=auto
export SQUADOPS_RUN_ROOT="${SQUADOPS_RUN_ROOT:-$HOME/.cache/squadops/bench-runs}"
mkdir -p "$SQUADOPS_RUN_ROOT"
exec goose session --name "bench-$ROLE" --system "$SYSTEM" --with-builtin developer
