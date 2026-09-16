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
LOGDIR="${NOSTROMO_LOGDIR:-/opt/nostromo/logs/$ROLE}"
# Manifest picks the harness; NOSTROMO_HARNESS overrides it for an A/B run without a commit.
HARNESS="${NOSTROMO_HARNESS:-}"
MANIFEST="$REPO/crew/manifest.yaml"
ALLOWFILE="$REPO/crew/allowlist.yaml"
PERSONA="$REPO/crew/personas/$ROLE.md"
INSTRUCTIONS="$REPO/instructions.md"
BASE_PROMPT="$REPO/crew/prompts/base-$ROLE.md"

die() { echo "launch-$ROLE: $*" >&2; exit 1; }

# A role's identity is which uid is running, not which name is passed. Same guard as mint-token.sh.
[[ "$(id -un)" == "$ROLE" ]] || die "must run as $ROLE, not $(id -un)"

# The runtime is not on a login shell's PATH. Source the file install-base.sh wrote rather than
# re-deriving it here, so there is one definition of where the runtime lives.
#
# This matters twice over: buzz-acp spawns `buzz-agent` by name, AND the agent speaks by running
# `buzz` through its MCP shell tool — both live here. A missing PATH fails loudly for the first and SILENTLY for the second,
# which is a mute agent with a healthy-looking process. Hand-launching hid this by inheriting an
# interactive shell's PATH.
ENV_SH="${NOSTROMO_ENV:-/opt/nostromo/runtime/env.sh}"
[[ -r "$ENV_SH" ]] || die "missing $ENV_SH — was install-base.sh run on this host?"
# shellcheck source=/dev/null
source "$ENV_SH"
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

for f in "$MANIFEST" "$ALLOWFILE" "$PERSONA" "$INSTRUCTIONS" "$BASE_PROMPT"; do
  [[ -r "$f" ]] || die "missing or unreadable: $f  (run push-repo.sh from the Mac)"
done

[[ -n "$HARNESS" ]] || HARNESS="$(yaml_agent harness)"
case "$HARNESS" in buzz-agent|goose) ;; *) die "unsupported harness '$HARNESS' — expected buzz-agent or goose" ;; esac

for b in buzz-acp "$HARNESS" buzz-dev-mcp buzz; do
  command -v "$b" >/dev/null 2>&1 || die "$b is not on PATH after sourcing $ENV_SH"
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

# NIP-OA owner attestation. Without it `buzz mem set` fails with "owner pubkey required", so the
# agent cannot write core memory — and buzz-acp injects an onboarding nudge every turn telling it
# to do exactly that, which it then cannot do. The tag is public (it proves owner->agent binding;
# acting as the agent still needs the agent's key), so it lives in the manifest. Mint it with
# infrastructure/buzz/bin/mint-auth-tags.py on the machine holding the owner key.
AUTH_TAG="$(yaml_agent buzz_auth_tag)"
AUTH_TAG="${AUTH_TAG%\'}"; AUTH_TAG="${AUTH_TAG#\'}"
# ${VAR:-default} yields the VALUE when VAR is set, so a :+/:- pair prints the tag itself.
AUTH_DESC="ABSENT — core memory will not persist"
[[ -n "$AUTH_TAG" ]] && AUTH_DESC="present, ${#AUTH_TAG} bytes"
if [[ -n "$AUTH_TAG" ]]; then
  export BUZZ_AUTH_TAG="$AUTH_TAG"
else
  echo "launch-$ROLE: WARNING no buzz_auth_tag in the manifest — core memory will not persist," >&2
  echo "launch-$ROLE:         and the harness nudges for one every turn. See mint-auth-tags.py." >&2
fi


# ---- §13.2.10 buzz-agent → local Ollama/Qwen ------------------------------------------------
# Mother is local-inference-only (crew constitution, "Budget and blocked state"). buzz-agent takes
# its provider from the environment, so assert it here rather than trusting it: on 2026-09-15 an
# OpenCode profile with no provider block silently served a turn from a hosted model, with no error
# and nothing in Ollama's journal. Fail closed instead.
OLLAMA_TAG="$(yaml_agent ollama_tag)"
PROVIDER="$(yaml_agent provider)"
[[ "$PROVIDER" == "ollama" ]] || die "manifest says provider=$PROVIDER; $ROLE is local-inference-only"
[[ -n "$OLLAMA_TAG" ]] || die "no ollama_tag for $ROLE in the manifest"

OLLAMA_URL="http://localhost:11434"
curl -sf --max-time 5 "$OLLAMA_URL/api/tags" -o /tmp/.nostromo-tags.$$ \
  || die "Ollama is not answering on $OLLAMA_URL"
python3 -c 'import json,sys; ms=[m["name"] for m in json.load(open(sys.argv[1]))["models"]]; sys.exit(0 if sys.argv[2] in ms else 1)' \
  /tmp/.nostromo-tags.$$ "$OLLAMA_TAG" || { rm -f /tmp/.nostromo-tags.$$; die "Ollama has no model tagged $OLLAMA_TAG"; }
rm -f /tmp/.nostromo-tags.$$

# ---- §13.2.1/2 prompt layering, §13.2.9 no MCP ----------------------------------------------
# §13.2.9: no MCP child tool. buzz-dev-mcp is a developer toolkit (shell, file read, atomic edit);
# wiring it here would hand Mother the file-editing tools her permission profile denies.
#
# Prompt layering, from `buzz-acp --help`:
#   <base>               --base-prompt-file. buzz-acp's compiled-in default is 18,239 characters
#                        of coding-agent brief — worktrees, AGENTS.md, git trailers, committing —
#                        for a role with edit/write denied and no repo. The delivery contract it
#                        does carry ("you MUST publish", "you MUST reply") sits ~80 lines deep,
#                        and Mother honoured it about half the time. base-mother.md keeps that
#                        contract, puts it first, and drops the rest: 2.7 KB instead of 18 KB.
#
#                        Two removals are deliberate, not just trimming:
#                        - "Autonomy" told her to resolve questions herself and pick the safest
#                          option rather than surface them. Her job is escalating what is not
#                          hers to decide; that section argued against it every turn.
#                        - "publishing is optional and silence is usually correct" is true for an
#                          agent watching a busy channel. Mother only ever runs because she was
#                          mentioned, so for her, silence is never the right answer.
#
#                        Never --no-base-prompt: that drops the CLI contract entirely and makes
#                        her mute, which is how she failed on 2026-09-15.
#
#                        NOTE: buzz-agent's reply guard (BUZZ_AGENT_REQUIRE_REPLY below) documents
#                        that it deliberately tolerates silence because the stock base prompt says
#                        "publishing is optional and silence is usually correct". base-mother.md
#                        removes that line on purpose — she only ever runs when mentioned — so the
#                        guard and the prompt point the same way rather than against each other.
#
# Session size is NOT why she goes quiet. Delivery looked size-separated over four turns, but an
# owner-escalation on a fresh 10,087-token session failed too. The real split is who she is
# addressing: crew routing delivered 4/5, owner escalation 0/3. See the persona's escalation block.
#   <agent-instructions> --system-prompt-file, the persona
#   <team-instructions>  --team-instructions, the crew constitution
#
# NIP-AE core memory stays ON (buzz-acp's default). It is a signed kind:30174 on the relay — the
# same durable external storage the constitution asks for — and what Mother writes there is
# readable under $LOGDIR, so it can be judged on evidence rather than assumed to be a risk.
TEAM_INSTRUCTIONS="$(cat "$INSTRUCTIONS")"

cat <<INFO
launch-$ROLE: resolved configuration
  repo            $REPO @ $(git -c safe.directory="$REPO" -C "$REPO" log --oneline -1 2>/dev/null || echo unknown)
  identity        $MANIFEST_PUB
  relay           $RELAY_URL
  respond-to      $RESPOND_TO ($(awk -F, '{print NF}' <<<"$ALLOWLIST") allowlisted + owner)
  base prompt     $BASE_PROMPT ($(wc -c <"$BASE_PROMPT") bytes, vs 18239 compiled-in)
  persona         $PERSONA
  instructions    $INSTRUCTIONS ($(wc -c <"$INSTRUCTIONS") bytes)
  harness         $HARNESS + buzz-dev-mcp (shell, read_file, str_replace, todo, view_image)
  model           $OLLAMA_TAG via $OLLAMA_URL/v1 (provider=$PROVIDER)
  max rounds      ${NOSTROMO_MAX_ROUNDS:-12}
  workdir         $WORKDIR
  logs            $LOGDIR
  auth tag        $AUTH_DESC
  runtime         $(dirname "$(command -v buzz-acp)")  (buzz: $(command -v buzz))
INFO

[[ "${1:-}" == "--print" ]] && exit 0

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

# An agent whose logs live in a 700 home costs the operator a sudo round trip per question, which
# on 2026-09-15 is most of what diagnosing this role cost. Point OpenCode's data dir at a
# group-readable location under /opt/nostromo so the supervisor account can read it directly.
# Contents are prompts and channel text, both of which already exist in the relay; no key is
# written here (buzz-acp logs the PUBLIC key only).
# Logs a role can delete are not evidence. On 2026-09-16 this directory was created group-writable
# under group `nostromo`, which every role is a member of — so any role could have destroyed any
# other role's record, and Mother had a shell. The repo hit the same class of bug in a89dc91.
# Provisioned by root (create-role-accounts.sh); asserted here so a mis-provisioned role fails
# loudly at launch rather than logging into a directory its siblings can empty.
[[ -d "$LOGDIR" ]] || die "$LOGDIR does not exist — provision it as root, owner $ROLE, group nostromo, mode 2750"
LOGDIR_OWNER="$(stat -c '%U' "$LOGDIR")"
LOGDIR_MODE="$(stat -c '%a' "$LOGDIR")"
[[ "$LOGDIR_OWNER" == "$ROLE" ]] || die "$LOGDIR is owned by $LOGDIR_OWNER, must be $ROLE"
[[ "$LOGDIR_MODE" == "2750" ]] || die "$LOGDIR is mode $LOGDIR_MODE, must be 2750 (no group write)"

export XDG_DATA_HOME="$LOGDIR/xdg"
umask 007
install -d -m 2770 "$XDG_DATA_HOME" 2>/dev/null || true

# buzz-agent's provider, from the manifest rather than from whatever is in the environment.
# OPENAI_COMPAT_* is the OpenAI-compatible path; buzz-agent's own docs name Ollama as a target.
# The API key is required by the provider contract and ignored by Ollama — it is not a secret.
if [[ "$HARNESS" == "buzz-agent" ]]; then
  export BUZZ_AGENT_PROVIDER=openai
  export OPENAI_COMPAT_BASE_URL="$OLLAMA_URL/v1"
  export OPENAI_COMPAT_MODEL="$OLLAMA_TAG"
  export OPENAI_COMPAT_API_KEY=ollama-local-no-auth
  # The reason for this harness. buzz-agent reminds the model when a turn is about to end with no
  # recognized `buzz messages send` — the exact failure that lost a third of Mother's answers
  # under OpenCode. Advisory: at most two reminders, then the turn ends regardless.
  export BUZZ_AGENT_REQUIRE_REPLY=1
  # BUZZ_AGENT_MAX_ROUNDS defaults to 0 — unlimited tool rounds. On 2026-09-16 Mother published
  # the same routing answer five times in 56 seconds and was still going at 48 LLM calls; every
  # tool call reported "completed", so nothing was failing and nothing was going to stop her. The
  # only other backstops are --max-turn-duration (2h) and --idle-timeout (25m), both far too long
  # for a shared GPU. A routing turn needs a handful of rounds; a verification turn needs more,
  # which is why this is per-role rather than global.
  export BUZZ_AGENT_MAX_ROUNDS="${NOSTROMO_MAX_ROUNDS:-12}"
  HARNESS_ARGS=""
else
  # Goose speaks to Ollama natively rather than through an OpenAI-compatible shim.
  export GOOSE_PROVIDER=ollama
  export GOOSE_MODEL="$OLLAMA_TAG"
  export OLLAMA_HOST="$OLLAMA_URL"
  # Unattended: Goose's permission flow is interactive (AllowOnce/DenyOnce/AlwaysDeny), and an
  # agent nobody is watching cannot answer a prompt. What Mother can do is therefore decided by
  # which MCP servers are wired below, not by this mode.
  export GOOSE_MODE=auto
  # NOTE: Goose has no equivalent of BUZZ_AGENT_REQUIRE_REPLY. It knows nothing about Buzz, so a
  # turn that ends without `buzz messages send` is silently lost, exactly as under OpenCode.
  # Whether that matters is what this A/B measures.
  HARNESS_ARGS="acp"
fi

# NOSTROMO_ACP_TRACE=1 routes the agent's stdio through acp-tee.sh, capturing the full JSON-RPC
# stream — including assistant text that is never published. Off by default: it inserts two
# processes into the protocol's critical path, and an agent that works is worth more than one we
# can fully read. Turn it on to diagnose a turn, off again afterwards.
AGENT_CMD="$HARNESS"
AGENT_ARGS=()
[[ -n "$HARNESS_ARGS" ]] && AGENT_ARGS=(--agent-args "$HARNESS_ARGS")
if [[ -n "${NOSTROMO_ACP_TRACE:-}" ]]; then
  TEE="$REPO/infrastructure/spark/bin/acp-tee.sh"
  [[ -x "$TEE" ]] || die "NOSTROMO_ACP_TRACE set but $TEE is not executable"
  AGENT_CMD="$TEE"
  # One value per --agent-args flag: buzz-acp collects them into a Vec, it does not split on
  # whitespace. Passing "$LOGDIR $HARNESS" as one value handed the tee a single argument and no
  # agent command at all.
  AGENT_ARGS=(--agent-args "$LOGDIR" --agent-args "$HARNESS")
  [[ -n "$HARNESS_ARGS" ]] && AGENT_ARGS+=(--agent-args "$HARNESS_ARGS")
  echo "launch-$ROLE: ACP tracing ON — stdio captured to $LOGDIR/acp/" >&2
fi

export BUZZ_PRIVATE_KEY="$(cat "$KEYFILE")"
export BUZZ_RELAY_URL="$RELAY_URL"

# exec, so the process this script starts is the process a supervisor will later watch and signal.
exec buzz-acp \
  --agent-command "$AGENT_CMD" ${AGENT_ARGS[@]+"${AGENT_ARGS[@]}"} \
  --mcp-command buzz-dev-mcp \
  --agent-owner "$OWNER_PUB" \
  --respond-to "$RESPOND_TO" \
  --respond-to-allowlist "$ALLOWLIST" \
  --allowed-respond-to owner-only,allowlist \
  --base-prompt-file "$BASE_PROMPT" \
  --system-prompt-file "$PERSONA" \
  --team-instructions "$TEAM_INSTRUCTIONS" \
  --session-title "$ROLE"
