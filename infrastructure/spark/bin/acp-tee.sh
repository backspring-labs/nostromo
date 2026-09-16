#!/usr/bin/env bash
# Tee an ACP agent's stdio to a file, then exec the agent. OPT-IN: see NOSTROMO_ACP_TRACE.
#
# ACP is JSON-RPC over stdio, so everything between buzz-acp and the agent passes through here:
# the composed prompt, every tool call, and every agent_message_chunk — including the assistant
# text buzz-acp discards rather than publishing. That text was readable under OpenCode and Goose
# (both keep a session database) and was lost when we moved to buzz-agent, whose README says
# plainly: "No persistence."
#
# Not --relay-observer: KIND_AGENT_OBSERVER_FRAME (24200) is in the ephemeral range and is never
# stored, so it answers "watch a turn live", not "what did she say ten minutes ago".
#
# Buffering matters. tee block-buffers when stdout is not a tty, and a JSON-RPC frame sitting in a
# 4 KB buffer deadlocks the protocol — the agent waits for a request that is still in flight.
# stdbuf -i0 -o0 forces unbuffered on every stage.
#
# Usage:  acp-tee.sh <logdir> <agent-command> [args...]
set -uo pipefail
LOGDIR="${1:?usage: acp-tee.sh <logdir> <agent-command> [args...]}"; shift
AGENT="${1:?no agent command}"; shift

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
umask 007
mkdir -p "$LOGDIR/acp" 2>/dev/null || true

# The prompt carries channel content, not secrets: BUZZ_PRIVATE_KEY reaches the agent through the
# environment and never crosses stdio. Files land in the role's own 2750 directory.
exec stdbuf -i0 -o0 tee -a "$LOGDIR/acp/$STAMP.in.jsonl" \
  | stdbuf -i0 -o0 "$AGENT" "$@" \
  | stdbuf -i0 -o0 tee -a "$LOGDIR/acp/$STAMP.out.jsonl"
