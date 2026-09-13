#!/usr/bin/env bash
# Verify that the Nostromo crew account is contained (NOSTROMO-PLAN-0001 §11, NOSTROMO-0002 §45.4).
#
# Run AS THE CREW USER, not as root: ssh nostromo@spark 'bash -s' < verify-crew-boundary.sh
# Running it as the crew user is the point — it tests the boundary from the position an agent
# actually occupies, rather than from root's simulation of it.
#
# Exit 0 only if every check behaves as required. Safe to re-run; changes nothing.
set -uo pipefail

OWNER="${OWNER:-jladd}"
RUNTIME_ROOT="${RUNTIME_ROOT:-/opt/nostromo}"
fail=0

# `expect` is exactly "pass" or "fail" — the status the command must produce. An invalid value is
# itself a failure, because a comparison that can never match reports a green boundary as broken
# and a broken one as green.
check() {
  local desc="$1" expect="$2"; shift 2
  if [[ "$expect" != "pass" && "$expect" != "fail" ]]; then
    printf '  ERROR %s (bad expectation %q; must be pass or fail)\n' "$desc" "$expect"; fail=1; return
  fi
  local got
  if bash -c "$*" >/dev/null 2>&1; then got=pass; else got=fail; fi
  if [[ "$got" == "$expect" ]]; then
    printf '  PASS  %s\n' "$desc"
  else
    printf '  FAIL  %s — expected the command to %s, it %sed\n' "$desc" "$expect" "$got"; fail=1
  fi
}

echo "verifying the crew boundary as $(id -un) (uid $(id -u), groups: $(id -nG))"
echo

echo "must be denied:"
check "read the owner's SSH private key"   fail "cat /home/$OWNER/.ssh/id_ed25519"
check "read the owner's gh token"          fail "cat /home/$OWNER/.config/gh/hosts.yml"
check "list the owner's home"              fail "ls /home/$OWNER"
check "read the owner's squad-ops clone"   fail "ls /home/$OWNER/Code/squad-ops"
check "reach the docker socket"            fail "docker ps"
check "sudo"                               fail "sudo -n true"
check "write the owner's home"             fail "touch /home/$OWNER/.nostromo-probe"

echo
echo "must be permitted:"
check "write its own home"                 pass "touch ~/.nostromo-probe && rm ~/.nostromo-probe"
check "write the runtime root"             pass "touch $RUNTIME_ROOT/.probe && rm $RUNTIME_ROOT/.probe"
check "reach Ollama over HTTP"             pass "curl -fsS http://localhost:11434/api/version"
check "reach github.com"                   pass "curl -fsS -o /dev/null https://api.github.com"

echo
if [[ $fail == 0 ]]; then
  echo "all checks behaved as required; the crew account is contained and functional"
else
  echo "SOME CHECKS DID NOT BEHAVE AS REQUIRED — do not run crew agents until they do" >&2
fi
exit $fail
