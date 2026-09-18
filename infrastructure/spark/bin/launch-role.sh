#!/usr/bin/env bash
# The Nostromo crew launcher — Bootstrap Plan §13.9. Runs ON the Spark, AS the role.
#
# Generalised from the explicit Mother and Brett adapters, in that order, because the plan is
# deliberate about it: abstracting from one instance bakes in that instance's shape. With two
# built, the diff was three real differences — working directory, round budget, whether a clone
# is required — and everything else already derived from the role name. Those three now live in
# crew/manifest.yaml, so a new role is a manifest entry and a persona, not a copied file.
#
# The plan calls for one explicit adapter before a generic launcher, so the twelve steps are
# visible and a failure is attributable to a step rather than to "the launch". Every value is
# resolved from the repo under /opt/nostromo; nothing is typed at the prompt, because a
# hand-typed launch is not reproducible and the other six roles have to come from somewhere.
#
# Usage (as the role, on the Spark):  launch-role.sh <role> [--print]
#   --print   resolve and show the configuration, then exit without launching
set -euo pipefail

ROLE="${1:?usage: launch-role.sh <role> [--print]}"; shift
REPO="${NOSTROMO_REPO:-/opt/nostromo/nostromo-src}"
RUNTIME_BIN="${NOSTROMO_RUNTIME_BIN:-/opt/nostromo/runtime/bin}"
SECRETS="$HOME/.config/nostromo/secrets"
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
case "$HARNESS" in buzz-agent|goose|claude-agent-acp|codex-acp) ;; *) die "unsupported harness '$HARNESS'" ;; esac

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

# ---- per-role shape, from the manifest -------------------------------------------------------
# Three values that genuinely differ between roles. Everything else derives from $ROLE.
WORKDIR="$(yaml_agent workdir)"
WORKDIR="${WORKDIR/#\~/$HOME}"
[[ -n "$WORKDIR" ]] || die "no workdir for $ROLE in the manifest"
# A pinned model and the family it is supposed to belong to must agree. Dallas reviews with a
# different provider/model family from the roles whose work he reviews — that is the design, not a
# preference — and a pin quietly changed to another family would defeat it while the manifest
# still claimed otherwise. Documentation that can drift from what runs is documentation that lies.
MODEL_FAMILY="$(yaml_agent model_family)"
PINNED="$(yaml_agent model)"
if [[ -n "$MODEL_FAMILY" && -n "$PINNED" ]]; then
  [[ "$PINNED" == *"$MODEL_FAMILY"* ]] \
    || die "manifest says model_family=$MODEL_FAMILY but model=$PINNED — they disagree; change both or neither"
fi

REQUIRES_CLONE="$(yaml_agent requires_clone)"
MAX_ROUNDS="$(yaml_agent max_rounds)"
[[ -n "$MAX_ROUNDS" ]] || die "no max_rounds for $ROLE in the manifest"

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


# ---- provider ---------------------------------------------------------------------------------
# Whatever the manifest says the provider is, assert it rather than trust it. On 2026-09-15 an
# OpenCode profile with no provider block silently served a turn from a hosted model, with no
# error anywhere and nothing in Ollama's journal. Fail closed instead.
PROVIDER="$(yaml_agent provider)"
[[ -n "$PROVIDER" ]] || die "no provider for $ROLE in the manifest"
OLLAMA_URL="http://localhost:11434"
OLLAMA_TAG="$(yaml_agent ollama_tag)"
PROVIDER_KEY=""

case "$PROVIDER" in
  ollama)
    # Local inference. The constitution binds Mother and Brett to it: "A slow local model is not a
    # reason to use a cloud model." Assert the model is actually resident, or the first turn fails
    # inside a live channel rather than here.
    [[ -n "$OLLAMA_TAG" ]] || die "no ollama_tag for $ROLE in the manifest"
    curl -sf --max-time 5 "$OLLAMA_URL/api/tags" -o /tmp/.nostromo-tags.$$ \
      || die "Ollama is not answering on $OLLAMA_URL"
    python3 -c 'import json,sys; ms=[m["name"] for m in json.load(open(sys.argv[1]))["models"]]; sys.exit(0 if sys.argv[2] in ms else 1)' \
      /tmp/.nostromo-tags.$$ "$OLLAMA_TAG" || { rm -f /tmp/.nostromo-tags.$$; die "Ollama has no model tagged $OLLAMA_TAG"; }
    rm -f /tmp/.nostromo-tags.$$
    ;;
  anthropic|openai)
    # Metered. The key is bytes on disk in the role's own 600 file — the same shape as its Nostr
    # key, and deliberately not an OAuth session: nothing to refresh, nothing interactive, so a
    # reboot is a non-event. Never in the repo, never in the environment of another role.
    #
    # "Use only your own provider boundary. Never borrow another agent's credential." Each metered
    # role has its own key and its own budget, so spend is attributable rather than pooled.
    PROVIDER_KEY="$SECRETS/$PROVIDER.key"
    [[ -r "$PROVIDER_KEY" ]] || die "no $PROVIDER key at $PROVIDER_KEY"
    kmode="$(stat -c '%a' "$PROVIDER_KEY")"
    [[ "$kmode" == "600" ]] || die "$PROVIDER_KEY is mode $kmode, must be 600"
    [[ -n "$PINNED" ]] || die "no model for $ROLE in the manifest — a metered role must pin one"
    ;;
  *)
    die "unsupported provider '$PROVIDER' for $ROLE"
    ;;
esac

# ---- §13.2.1/2 prompt layering, §13.2.9 no MCP ----------------------------------------------
# §13.2.9: no MCP child tool. buzz-dev-mcp is a developer toolkit (shell, file read, atomic edit);
# it is the toolkit Brett works through: shell, read_file, str_replace, todo, view_image.
#
# Prompt layering, from `buzz-acp --help`:
#   <base>               --base-prompt-file. buzz-acp's compiled-in default is 18,239 characters
#                        of coding-agent brief — worktrees, AGENTS.md, git trailers, committing —
#                        for a role with edit/write denied and no repo. The delivery contract it
#                        does carry ("you MUST publish", "you MUST reply") sits ~80 lines deep,
#                        and Mother honoured it about half the time. base-<role>.md keeps that
#                        contract and puts it first, and keeps Engineering Discipline and
#                        Working in the Repo, which a verification role does need.
#
#                        Two removals are deliberate, not just trimming:
#                        - "Autonomy" told her to resolve questions herself and pick the safest
#                          option rather than surface them. Her job is escalating what is not
#                          hers to decide; that section argued against it every turn.
#                        - "publishing is optional and silence is usually correct" is true for an
#                          agent watching a busy channel. A crew member only ever runs because
#                          it was mentioned, so for it, silence is never the right answer.
#
#                        Never --no-base-prompt: that drops the CLI contract entirely and makes
#                        her mute, which is how she failed on 2026-09-15.
#
#                        NOTE: buzz-agent's reply guard (BUZZ_AGENT_REQUIRE_REPLY below) documents
#                        that it deliberately tolerates silence because the stock base prompt says
#                        "publishing is optional and silence is usually correct". base-<role>.md
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
# same durable external storage the constitution asks for — and what a role writes there is
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
  provider        $PROVIDER${PROVIDER_KEY:+  (key: $PROVIDER_KEY, contents never shown)}
  model           ${PINNED:-$OLLAMA_TAG}${OLLAMA_TAG:+  via $OLLAMA_URL/v1}
  max rounds      ${NOSTROMO_MAX_ROUNDS:-$MAX_ROUNDS}
  workdir         $WORKDIR
  logs            $LOGDIR
  auth tag        $AUTH_DESC
  runtime         $(dirname "$(command -v buzz-acp)")  (buzz: $(command -v buzz))
INFO

[[ "${1:-}" == "--print" ]] && exit 0

# ---- working directory ------------------------------------------------------------------------
# A role that verifies against real code works in its own clone; a router needs no files at all.
# A clone, not a git worktree: worktrees write metadata back into one shared bare repository,
# which would mean every role holding write access to the same directory.
if [[ "$REQUIRES_CLONE" == "true" ]]; then
  [[ -d "$WORKDIR/.git" ]] || die "no clone at $WORKDIR — run provision-clone.sh as $ROLE first"
else
  install -d -m 700 "$WORKDIR"
fi

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
case "$HARNESS" in
  buzz-agent)
    export BUZZ_AGENT_PROVIDER=openai
    export OPENAI_COMPAT_BASE_URL="$OLLAMA_URL/v1"
    export OPENAI_COMPAT_MODEL="$OLLAMA_TAG"
    export OPENAI_COMPAT_API_KEY=ollama-local-no-auth
    # The reason for this harness. buzz-agent reminds the model when a turn is about to end with
    # no recognized `buzz messages send` — the failure that lost a third of Mother's answers under
    # OpenCode, and that reproduced on Goose. Advisory: two reminders, then the turn ends.
    export BUZZ_AGENT_REQUIRE_REPLY=1
    # MAX_ROUNDS defaults to 0, meaning unlimited: Mother reached 48 rounds republishing one
    # answer before this was capped. The cap is silent when it fires — buzz-agent returns
    # StopReason::MaxTurnRequests and publishes nothing — so personas are told to leave evidence
    # on disk as they go.
    export BUZZ_AGENT_MAX_ROUNDS="${NOSTROMO_MAX_ROUNDS:-$MAX_ROUNDS}"
    HARNESS_ARGS=""
    ;;
  goose)
    export GOOSE_PROVIDER=ollama
    export GOOSE_MODEL="$OLLAMA_TAG"
    export OLLAMA_HOST="$OLLAMA_URL"
    # Unattended: Goose's permission flow is interactive (AllowOnce/DenyOnce/AlwaysDeny) and an
    # agent nobody is watching cannot answer a prompt. Capability comes from the wired MCP server.
    export GOOSE_MODE=auto
    # Goose has no equivalent of BUZZ_AGENT_REQUIRE_REPLY and cannot: it knows nothing about Buzz.
    # A turn ending without `buzz messages send` is silently lost — observed, not theorised.
    HARNESS_ARGS="acp"
    ;;
  claude-agent-acp|codex-acp)
    # Metered harnesses take their credential from the provider's standard variable. Read from the
    # role's own 600 file at launch and never written anywhere: not into the repo, not into a
    # config file, not into another role's environment.
    if [[ "$PROVIDER" == "anthropic" ]]; then
      export ANTHROPIC_API_KEY="$(cat "$PROVIDER_KEY")"
    else
      export OPENAI_API_KEY="$(cat "$PROVIDER_KEY")"
      # codex-acp advertises two ACP auth methods — `api-key` and `chat-gpt` — and the key is only
      # "the fallback API key used when the API-key auth method is selected". Setting the key alone
      # leaves the adapter unauthenticated: it answered every prompt with
      # "Agent reported error (code -32000): Authentication required" and buzz-acp requeued with
      # backoff forever. DEFAULT_AUTH_REQUEST selects the method without a client round-trip.
      export DEFAULT_AUTH_REQUEST='{"methodId":"api-key"}'
      # Nothing here has a browser, and a role must never be waiting on an interactive login.
      export NO_BROWSER=1
    fi
    # These agents take the model through buzz-acp rather than an env var of their own.
    HARNESS_ARGS=""
    ;;
  *)
    die "unsupported harness '$HARNESS' for $ROLE"
    ;;
esac

# NOSTROMO_ACP_TRACE=1 routes the agent's stdio through acp-tee.sh, capturing the full JSON-RPC
# stream — including assistant text that is never published. Off by default: it inserts two
# processes into the protocol's critical path, and an agent that works is worth more than one we
# can fully read. Turn it on to diagnose a turn, off again afterwards.
# buzz-agent reads its model from the environment; the ACP adapters take it from buzz-acp.
MODEL_ARG=()
[[ "$HARNESS" != "buzz-agent" && "$HARNESS" != "goose" && -n "$PINNED" ]] && MODEL_ARG=(--model "$PINNED")
# Optional, and only meaningful for adapters that implement session/set_config_option. Left unset
# unless the manifest asks for it, because buzz-acp's own default is bypass-permissions and
# guessing at an adapter's permission semantics is how a role ends up unable to read anything.
PERMISSION_ARG=()
PERM="$(yaml_agent permission_mode)"
[[ -n "$PERM" ]] && PERMISSION_ARG=(--permission-mode "$PERM")

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

# SquadOps materialises run roots under /tmp/squadops unless told otherwise. That path is shared
# by every Unix user on this box and is already owned by the owner's account from their own runs,
# so a role cannot write it: 109 tests failed on a PermissionError that surfaced as "coroutine
# raised StopIteration" (wp4-worktrees evidence). A root per role also stops two roles colliding.
export SQUADOPS_RUN_ROOT="${SQUADOPS_RUN_ROOT:-$HOME/.cache/squadops/runs}"
mkdir -p "$SQUADOPS_RUN_ROOT"

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
  ${MODEL_ARG[@]+"${MODEL_ARG[@]}"} \
  ${PERMISSION_ARG[@]+"${PERMISSION_ARG[@]}"} \
  --system-prompt-file "$PERSONA" \
  --team-instructions "$TEAM_INSTRUCTIONS" \
  --session-title "$ROLE" \
  --multiple-event-handling queue
