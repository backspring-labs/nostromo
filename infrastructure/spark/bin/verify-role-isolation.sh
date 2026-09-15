#!/usr/bin/env bash
# Verify that each crew role is isolated from the others, FROM INSIDE each account.
#
# Run from the Mac: infrastructure/spark/bin/verify-role-isolation.sh
#
# It ssh's into each role and runs the checks there, because that is the position an agent actually
# occupies. Root simulating it with `sudo -u` is a weaker test — and an earlier version of the
# owner-boundary check reported a holding boundary as eight failures by comparing against the wrong
# string, so these checks name exactly what they expect and reject a malformed expectation.
set -uo pipefail

ROLES=(mother ash ripley dallas parker brett lambert)
HOST="${SPARK_HOST:-spark}"
SUPERVISOR=nostromo
fail=0

probe() {   # probe <role>
  local role="$1" other
  # Pick a different role to test against, so "cannot read another role" is a real comparison.
  for r in "${ROLES[@]}"; do [[ "$r" != "$role" ]] && other="$r" && break; done

  ssh -o BatchMode=yes "$role@$HOST" "bash -s" <<EOF
set -uo pipefail
f=0
check() {
  local desc="\$1" expect="\$2"; shift 2
  if [[ "\$expect" != "pass" && "\$expect" != "fail" ]]; then
    printf '    ERROR %s (bad expectation)\n' "\$desc"; f=1; return
  fi
  local got; if bash -c "\$*" >/dev/null 2>&1; then got=pass; else got=fail; fi
  if [[ "\$got" == "\$expect" ]]; then printf '    PASS  %s\n' "\$desc"
  else printf '    FAIL  %s — expected to %s, it %sed\n' "\$desc" "\$expect" "\$got"; f=1; fi
}
echo "  $role (uid \$(id -u), groups: \$(id -nG))"
check "cannot read $other's home"              fail "ls /home/$other"
check "cannot read $other's secrets"           fail "cat /home/$other/.config/nostromo/secrets/* "
check "cannot read the supervisor's secrets"   fail "cat /home/$SUPERVISOR/.config/nostromo/secrets/*/*"
check "cannot read the owner's home"           fail "ls /home/jladd"
check "cannot reach the docker socket"         fail "docker ps"
check "cannot sudo"                            fail "sudo -n true"
check "cannot write the shared runtime"        fail "touch /opt/nostromo/.probe"
check "can write its own home"                 pass "touch ~/.probe && rm ~/.probe"
check "can write its own secret directory"     pass "touch ~/.config/nostromo/secrets/.p && rm ~/.config/nostromo/secrets/.p"
check "can READ the shared runtime"            pass "test -x /opt/nostromo/runtime/bin/node"
check "can reach Ollama"                       pass "curl -fsS http://localhost:11434/api/version"
exit \$f
EOF
}

for role in "${ROLES[@]}"; do
  probe "$role" || fail=1
  echo
done

if [[ $fail == 0 ]]; then
  echo "every role is isolated from every other, and from the owner"
else
  echo "AT LEAST ONE ROLE IS NOT ISOLATED — do not run agents until this passes" >&2
fi
exit $fail
