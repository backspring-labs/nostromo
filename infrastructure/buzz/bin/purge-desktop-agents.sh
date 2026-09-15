#!/usr/bin/env bash
# Remove every Buzz Desktop managed agent from this Mac, permanently.
#
# The Mac is the cockpit and runs no agents (Operating Model §35.4). Buzz Desktop disagrees: it
# provisions a trio per community joined, each with its own Nostr identity and a running buzz-acp
# process, and it recreates them whenever a `Welcome` channel is opened.
#
# ORDER MATTERS. Delete the `Welcome` channel in each community FIRST, in the app. That is the
# trigger — ensureWelcomeTeam() fires for a welcome channel and recreates any starter it cannot find
# for that relay URL. Purging agents while a Welcome channel still exists buys you minutes.
#
# This script removes the managed agents (identities, processes, logs, retention databases) and
# leaves the builtin PERSONAS alone: they hold no keys, run nothing, and cannot be deleted while the
# builtin team references them. An inert template is not an agent.
#
# Usage: purge-desktop-agents.sh [--dry-run]
set -euo pipefail
DRY=0
[[ "${1:-}" == "--dry-run" ]] && DRY=1

APP_DIR="$HOME/Library/Application Support/xyz.block.buzz.app"
AGENTS="$APP_DIR/agents/managed-agents.json"
[[ -f "$AGENTS" ]] || { echo "no Buzz agent config at $AGENTS"; exit 0; }

# Refuse while the app is running: it owns these files and will write over anything done underneath.
if pgrep -qx Buzz 2>/dev/null || pgrep -qf "/Applications/Buzz.app/Contents/MacOS/Buzz" 2>/dev/null; then
  echo "Buzz Desktop is running. Quit it first (Cmd-Q) — it owns these files and will rewrite them." >&2
  exit 1
fi

echo "== agents with an identity (these get removed)"
python3 - "$AGENTS" <<'PY'
import json, sys
for a in json.load(open(sys.argv[1])):
    if a.get("pubkey"):
        print(f"   {a['name']:8} {a['pubkey'][:16]}  relay={a.get('relay_url') or '(none)'}  respond_to={a.get('respond_to')}")
PY

if [[ $DRY == 1 ]]; then
  echo "== dry run; nothing changed"
  exit 0
fi

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="$HOME/.nostromo/backups/buzz-desktop-agents/$STAMP"
mkdir -p "$BACKUP"
cp -R "$APP_DIR/agents" "$BACKUP/"
echo "== backed up to $BACKUP"

# Keep only entries without a pubkey — the builtin personas. Remove every provisioned agent.
python3 - "$AGENTS" <<'PY'
import json, pathlib, sys
p = pathlib.Path(sys.argv[1])
agents = json.load(p.open())
keep = [a for a in agents if not a.get("pubkey")]
removed = [a for a in agents if a.get("pubkey")]
p.write_text(json.dumps(keep, indent=2))
print(f"== removed {len(removed)} agent(s); kept {len(keep)} inert persona(s)")
pathlib.Path("/tmp/.purged-pubkeys").write_text("\n".join(a["pubkey"] for a in removed))
PY

# Per-agent logs and retention databases are named by pubkey; take them with their agent.
if [[ -s /tmp/.purged-pubkeys ]]; then
  while read -r pk; do
    [[ -n "$pk" ]] || continue
    find "$APP_DIR/agents/logs" "$APP_DIR/agents/retention" -name "${pk}*" -delete 2>/dev/null || true
  done < /tmp/.purged-pubkeys
  rm -f /tmp/.purged-pubkeys
  echo "== removed their logs and retention databases"
fi

echo
echo "== verify"
pgrep -fl buzz-acp 2>/dev/null && echo "   WARNING: buzz-acp still running" || echo "   no buzz-acp processes"
python3 - "$AGENTS" <<'PY'
import json, sys
left = [a for a in json.load(open(sys.argv[1])) if a.get("pubkey")]
print("   agents with identities remaining:", len(left) or "none")
PY
echo
echo "Reopen Buzz. If a trio reappears, a Welcome channel still exists somewhere — delete it and rerun."
