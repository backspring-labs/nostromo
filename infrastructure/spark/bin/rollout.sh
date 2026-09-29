#!/usr/bin/env bash
# Restart crew roles onto whatever is now installed on the Spark — new buzz binaries (build-buzz.sh),
# a manifest, persona or prompt change (push-repo.sh), a model pin — a canary first. From the Mac.
#
#   rollout.sh [--wait N] [role...]     default: every enabled role, Mother first
#
# The first role is the canary and restarts alone. The rest follow, one at a time, only if it is still
# up after the wait — the same pid, no automatic restarts — and has re-authenticated on the relay.
#
# A restart CANCELS an in-flight turn. buzz-acp gives in-flight prompts 30 s to be cancelled, not to
# finish (its shutdown path, at 0cc63fe3), and nothing observable says beforehand that a turn is
# running, so roll out when the crew is not mid-conversation. Afterwards this reads each stop from the
# journal and reports any turn it cut. That works for roles logging at debug — the metered ones;
# Mother and Brett log at info, where the stop does not say.
#
# A role whose unit is disabled is never started by this, even when named: disabled is a decision
# (Ash is held until the owner authenticates it). Enable it deliberately first.
#
# The Spark may be running SquadOps cycles. A restart is light; it loads no model and runs no inference.
set -euo pipefail
SUP=nostromo@spark          # runs crewctl
OWN=spark                   # the owner's account, in group adm: reads the journal
NANO=nano
CREWCTL=/opt/nostromo/nostromo-src/infrastructure/spark/bin/crewctl
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
WAIT=30
ROLES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --wait) WAIT="${2:?--wait needs seconds}"; shift 2 ;;
    -*)     echo "unknown flag $1" >&2; exit 2 ;;
    *)      ROLES+=("$1"); shift ;;
  esac
done
die() { echo "rollout: $*" >&2; exit 1; }
say() { echo "== $*"; }

STATUS="$(ssh "$SUP" "$CREWCTL --json status")"
field() {  # role key -> value from the status snapshot passed on stdin
  python3 -c 'import json,sys
d = {r["role"]: r for r in json.load(sys.stdin)["crew"]}
print(d.get(sys.argv[1], {}).get(sys.argv[2], ""))' "$1" "$2"
}
if [[ ${#ROLES[@]} -eq 0 ]]; then
  while IFS= read -r r; do ROLES+=("$r"); done < <(python3 -c 'import json,sys
for r in json.load(sys.stdin)["crew"]:
    if r["enabled"] == "enabled": print(r["role"])' <<<"$STATUS")
fi
[[ ${#ROLES[@]} -gt 0 ]] || die "no enabled roles"
for r in "${ROLES[@]}"; do
  [[ "$(field "$r" enabled <<<"$STATUS")" == enabled ]] || die "$r is not enabled; this never starts a disabled role"
done
# A role budget-watch has paused stays down until its reset: restarting it only earns another refusal.
KEEP=()
for r in "${ROLES[@]}"; do
  until_="$(field "$r" paused_until <<<"$STATUS")"
  if [[ -n "$until_" && "$until_" != None ]]; then echo "   $r: skipped — paused by budget-watch until $until_"; else KEEP+=("$r"); fi
done
[[ ${#KEEP[@]} -gt 0 ]] || die "every requested role is paused by budget-watch"
ROLES=("${KEEP[@]}")
# Mother first when she is in the set: local inference, so a bad canary costs nothing.
ORDERED=()
for r in "${ROLES[@]}"; do [[ $r == mother ]] && ORDERED+=("$r"); done
for r in "${ROLES[@]}"; do [[ $r != mother ]] && ORDERED+=("$r"); done

pubkey() {
  python3 -c 'import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))["agents"][sys.argv[2]]["buzz_pubkey"])' \
    "$ROOT/crew/manifest.yaml" "$1"
}
BUILD="$(ssh "$SUP" 'cat /opt/nostromo/runtime/bin/buzz-build.commit 2>/dev/null || echo unrecorded')"
say "rolling out ${ORDERED[*]} onto buzz ${BUILD:0:10}; canary ${ORDERED[0]}; ${WAIT}s per role"

failed=0
for i in "${!ORDERED[@]}"; do
  r="${ORDERED[$i]}"
  since="$(date -u '+%Y-%m-%d %H:%M:%S')"
  out="$(ssh "$SUP" "$CREWCTL restart $r")"
  pid="$(sed -n 's/.*(pid \([0-9]*\).*/\1/p' <<<"$out")"
  [[ -n "$pid" ]] || { echo "   $r: restart did not report a pid: $out"; failed=1; break; }
  sleep "$WAIT"

  now="$(ssh "$SUP" "$CREWCTL --json status $r")"
  problems=""
  [[ "$(field "$r" active <<<"$now")" == active ]] || problems+=" not active;"
  [[ "$(field "$r" pid <<<"$now")" == "$pid" ]] || problems+=" pid changed ($pid -> $(field "$r" pid <<<"$now")), so it crashed and was restarted;"
  [[ "$(field "$r" restarts <<<"$now")" == 0 ]] || problems+=" $(field "$r" restarts <<<"$now") automatic restarts;"
  key="$(pubkey "$r")"
  # A short --tail, filtered on the relay's own timestamps — never docker's --since or a full read. The
  # power cut of 2026-09-28 left the relay's json log damaged at 16:15:21Z: any read that STARTS before
  # that point (--since, a full read, a long --tail) ends there, so nothing logged since is visible to
  # it. A --tail short enough to start after the damage reads fine. 1000 lines is hours of relay log,
  # far more than one rollout. A canary that had re-authenticated failed the --since check for this.
  auths="$(ssh "$NANO" "cd /mnt/ssd/buzz/deploy && ./buzzctl logs relay --tail 1000 2>/dev/null" \
           | grep -a 'NIP-42 auth successful' | grep -a "${key:0:8}" \
           | sed -nE 's/.*"timestamp":"([^"]+)".*/\1/p' | awk -v s="${since/ /T}" '$1 >= s' | wc -l | tr -d ' ')"
  [[ "$auths" -gt 0 ]] || problems+=" did not re-authenticate on the relay;"
  # The colour codes are stripped on the Spark: GNU sed reads \x1b, the Mac's does not.
  stop="$(ssh "$OWN" "journalctl -u nostromo@$r --since '$since UTC' --no-pager -o cat 2>/dev/null | sed -E 's/\x1b\[[0-9;]*m//g'" \
          | grep -E 'reaped (checked-out|idle) agent on shutdown|grace period expired' || true)"
  if grep -qE 'checked-out|grace period expired' <<<"$stop"; then
    turn="CUT A TURN IN PROGRESS — it was cancelled; resend it if it mattered"
  elif grep -q 'reaped idle' <<<"$stop"; then
    turn="was idle"
  else
    turn="turn state not logged at this level"
  fi

  if [[ -z "$problems" ]]; then
    echo "   $r: ok — pid $pid, re-authenticated, $turn"
  else
    echo "   $r: FAILED —$problems ($turn)"
    failed=1
    if [[ $i == 0 ]]; then
      echo "   the canary failed, so nothing else was restarted. Inspect: ssh $OWN journalctl -u nostromo@$r -n 50"
      break
    fi
  fi
done
[[ $failed == 0 ]] || die "rollout incomplete. If new binaries caused it, build-buzz.sh printed the rollback when it installed them"
say "done"
