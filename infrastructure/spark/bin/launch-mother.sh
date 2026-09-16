#!/usr/bin/env bash
# Mother's explicit launch adapter — Bootstrap Plan §13.2. Runs ON the Spark, AS mother.
#
# The plan calls for one explicit adapter before a generic launcher, so the twelve steps are
# visible and a failure is attributable to a step rather than to "the launch". Every value is
# resolved from the repo under /opt/nostromo; nothing is typed at the prompt, because a
# hand-typed launch is not reproducible and the other six roles have to come from somewhere.
#
# Usage (as mother, on the Spark):  launch-mother.sh [--print]
#   --print   resolve and show the configuration, then exit without launching
set -euo pipefail

ROLE=mother
REPO="${NOSTROMO_REPO:-/opt/nostromo/nostromo}"
RUNTIME_BIN="${NOSTROMO_RUNTIME_BIN:-/opt/nostromo/runtime/bin}"
SECRETS="$HOME/.config/nostromo/secrets"
WORKDIR="$HOME/workspace"          # §13.2.11
MANIFEST="$REPO/crew/manifest.yaml"
ALLOWFILE="$REPO/crew/allowlist.yaml"
PERSONA="$REPO/crew/personas/$ROLE.md"
INSTRUCTIONS="$REPO/instructions.md"
OPENCODE_SRC="$REPO/crew/opencode/$ROLE.json"

die() { echo "launch-$ROLE: $*" >&2; exit 1; }

# A role's identity is which uid is running, not which name is passed. Same guard as mint-token.sh.
[[ "$(id -un)" == "$ROLE" ]] || die "must run as $ROLE, not $(id -un)"

# The runtime is not on a login shell's PATH. Source the file install-base.sh wrote rather than
# re-deriving it here, so there is one definition of where the runtime lives.
#
# This matters twice over: buzz-acp spawns `opencode` by name, AND the agent speaks by running
# `buzz` — both live here. A missing PATH fails loudly for the first and SILENTLY for the second,
# which is a mute agent with a healthy-looking process. Hand-launching hid this by inheriting an
# interactive shell's PATH.
ENV_SH="${NOSTROMO_ENV:-/opt/nostromo/runtime/env.sh}"
[[ -r "$ENV_SH" ]] || die "missing $ENV_SH — was install-base.sh run on this host?"
# shellcheck source=/dev/null
source "$ENV_SH"
for b in buzz-acp opencode buzz; do
  command -v "$b" >/dev/null 2>&1 || die "$b is not on PATH after sourcing $ENV_SH"
done

# ---- small YAML readers -------------------------------------------------------------------
# The manifest is deliberately flat. Parsing it with awk keeps this script dependency-free on a
# box where a missing python module at launch time would read as "the agent is down".
yaml_top() {  # yaml_top <section> <key>
  awk -v s="$1" -v k="$2" '
    /^[a-z_]+:/ { ins = ($0 ~ "^" s ":") }
    ins && $1 == k":" { print $2; exit }' "$MANIFEST"
}
yaml_agent() {  # yaml_agent <key>   (under agents: <ROLE>:)
  awk -v r="$ROLE" -v k="$1" '
    /^agents:/ { ina = 1; next }
    ina && /^  [a-z]+:/ { role = $1; sub(":", "", role) }
    ina && role == r && $1 == k":" { print $2; exit }' "$MANIFEST"
}

for f in "$MANIFEST" "$ALLOWFILE" "$PERSONA" "$INSTRUCTIONS" "$OPENCODE_SRC"; do
  [[ -r "$f" ]] || die "missing or unreadable: $f  (run push-repo.sh from the Mac)"
done

# ---- §13.2.4 stable key, §13.2.3 secret file ------------------------------------------------
KEYFILE="$SECRETS/buzz.key"
PUBFILE="$SECRETS/buzz.pubkey"
[[ -r "$KEYFILE" ]] || die "no key at $KEYFILE"
MODE="$(stat -c '%a' "$KEYFILE")"
[[ "$MODE" == "600" ]] || die "$KEYFILE is mode $MODE, must be 600"

MANIFEST_PUB="$(yaml_agent buzz_pubkey)"
STORED_PUB="$(tr -d '[:space:]' < "$PUBFILE" 2>/dev/null || true)"
[[ -n "$MANIFEST_PUB" ]] || die "no buzz_pubkey for $ROLE in the manifest"
# Compare the STORED pubkey to the manifest rather than deriving it from the secret: deriving it
# would put the private key in argv, and /proc/<pid>/cmdline is world-readable. Derivation was
# verified when the key was minted and again by backup-crew-keys.sh.
[[ "$STORED_PUB" == "$MANIFEST_PUB" ]] \
  || die "identity mismatch — $PUBFILE is ${STORED_PUB:-empty}, manifest says $MANIFEST_PUB"

# ---- §13.2.5 relay, §13.2.6/7 inbound gate --------------------------------------------------
RELAY_URL="$(yaml_top relay url)"
OWNER_PUB="$(awk '$1 == "owner:" { print $2; exit }' "$ALLOWFILE")"
RESPOND_TO="$(yaml_agent respond_to)"
ALLOWLIST="$(awk -v r="$ROLE" '/^allowlists:/ { ina = 1; next } ina && $1 == r":" { print $2; exit }' "$ALLOWFILE")"
[[ -n "$RELAY_URL"  ]] || die "no relay.url in the manifest"
[[ -n "$OWNER_PUB"  ]] || die "no owner pubkey in $ALLOWFILE"
[[ -n "$ALLOWLIST"  ]] || die "no allowlist for $ROLE in $ALLOWFILE"
[[ -n "$RESPOND_TO" ]] || die "no respond_to for $ROLE in the manifest"

# ---- §13.2.10 OpenCode → local Ollama/Qwen --------------------------------------------------
# Mother is local-inference-only (crew constitution, "Budget and blocked state"). That is a claim
# about a config file, so assert it rather than trust it: on 2026-09-15 this script installed a
# profile with no provider block at all, OpenCode silently fell back to its own default, and a
# turn was served by a hosted model with no error anywhere. Fail closed instead.
PINNED_MODEL="$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("model",""))' "$OPENCODE_SRC")"
case "$PINNED_MODEL" in
  ollama/*) ;;
  "")  die "$OPENCODE_SRC pins no model — OpenCode would pick its own default provider" ;;
  *)   die "$OPENCODE_SRC pins '$PINNED_MODEL'; $ROLE is local-inference-only and needs an ollama/* model" ;;
esac
python3 -c 'import json,sys; c=json.load(open(sys.argv[1])); sys.exit(0 if "ollama" in c.get("provider",{}) else 1)' "$OPENCODE_SRC" \
  || die "$OPENCODE_SRC has no provider.ollama block"

# The model must actually be present locally, or the first turn fails inside a live channel.
OLLAMA_TAG="${PINNED_MODEL#ollama/}"
curl -sf --max-time 5 http://localhost:11434/api/tags -o /tmp/.nostromo-tags.$$ \
  || die "Ollama is not answering on localhost:11434"
python3 -c 'import json,sys; ms=[m["name"] for m in json.load(open(sys.argv[1]))["models"]]; sys.exit(0 if sys.argv[2] in ms else 1)' \
  /tmp/.nostromo-tags.$$ "$OLLAMA_TAG" || { rm -f /tmp/.nostromo-tags.$$; die "Ollama has no model tagged $OLLAMA_TAG"; }
rm -f /tmp/.nostromo-tags.$$

# ---- §13.2.1/2 prompt layering, §13.2.9 no MCP ----------------------------------------------
# §13.2.9: no MCP child tool. buzz-dev-mcp is a developer toolkit (shell, file read, atomic edit);
# wiring it here would hand Mother the file-editing tools her permission profile denies.
#
# Prompt layering, from `buzz-acp --help`:
#   <base>               compiled-in Buzz orientation — states that an agent speaks by running
#                        the `buzz` CLI. NOT overridden here; --no-base-prompt would remove it
#                        and make her mute, which is how she failed on 2026-09-15.
#   <agent-instructions> --system-prompt-file, the persona
#   <team-instructions>  --team-instructions, the crew constitution
TEAM_INSTRUCTIONS="$(cat "$INSTRUCTIONS")"

cat <<INFO
launch-$ROLE: resolved configuration
  repo            $REPO @ $(git -c safe.directory="$REPO" -C "$REPO" log --oneline -1 2>/dev/null || echo unknown)
  identity        $MANIFEST_PUB
  relay           $RELAY_URL
  respond-to      $RESPOND_TO ($(awk -F, '{print NF}' <<<"$ALLOWLIST") allowlisted + owner)
  persona         $PERSONA
  instructions    $INSTRUCTIONS ($(wc -c <"$INSTRUCTIONS") bytes)
  opencode        $HOME/.config/opencode/opencode.json
  model           $(python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("model","NONE PINNED"))' "$OPENCODE_SRC")
  workdir         $WORKDIR
  runtime         $(dirname "$(command -v buzz-acp)")  (buzz: $(command -v buzz))
INFO

[[ "${1:-}" == "--print" ]] && exit 0

install -d -m 700 "$HOME/.config/opencode"
install -m 600 "$OPENCODE_SRC" "$HOME/.config/opencode/opencode.json"

# ---- §13.2.11 non-destructive working directory ---------------------------------------------
# Not $HOME: OpenCode warns that a home directory is too broad ("Can not run certain FFF features
# in a file system root or home directories"), and `read: allow` over $HOME exposes ~/.config,
# which is where the key lives. Mother orchestrates and needs no files at all.
install -d -m 700 "$WORKDIR"

# The persona now arrives through the harness (below), so an AGENTS.md left in $HOME is a second,
# silently-competing source of instructions. Report it; do not delete the operator's file.
if [[ -e "$HOME/AGENTS.md" ]]; then
  echo "launch-$ROLE: WARNING $HOME/AGENTS.md still exists and is no longer the persona source." >&2
  echo "launch-$ROLE:         remove it once this launch is confirmed good." >&2
fi

# ---- §13.2.12 launch --------------------------------------------------------------------------
if pgrep -u "$ROLE" -x buzz-acp >/dev/null 2>&1; then
  die "buzz-acp is already running as $ROLE (pid $(pgrep -u "$ROLE" -x buzz-acp | tr '\n' ' ')) — stop it first"
fi

cd "$WORKDIR"
export BUZZ_PRIVATE_KEY="$(cat "$KEYFILE")"
export BUZZ_RELAY_URL="$RELAY_URL"

# exec, so the process this script starts is the process a supervisor will later watch and signal.
exec buzz-acp \
  --agent-command opencode \
  --agent-args acp \
  --agent-owner "$OWNER_PUB" \
  --respond-to "$RESPOND_TO" \
  --respond-to-allowlist "$ALLOWLIST" \
  --allowed-respond-to owner-only,allowlist \
  --system-prompt-file "$PERSONA" \
  --team-instructions "$TEAM_INSTRUCTIONS" \
  --session-title "$ROLE"
