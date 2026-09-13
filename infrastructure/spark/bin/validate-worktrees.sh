#!/usr/bin/env bash
# Bootstrap and validate each crew worktree (NOSTROMO-PLAN-0001 §11.6–§11.7).
#
# Runs ON the Spark as the crew account. The point of §11.7 is stated in the plan: prove any later
# failure is not simply a broken worktree. So this runs the repository's OWN gate —
# scripts/dev/run_regression_tests.sh, which is what CI runs — rather than a lighter substitute
# invented here. A worktree that passes the same gate as main is a worktree, not a suspect.
#
# Idempotent. Usage: validate-worktrees.sh [role ...]    (default: every worktree present)
set -uo pipefail

ROOT="${WORKTREE_ROOT:-$HOME/worktrees/squadops}"
roles=("$@")
if [[ ${#roles[@]} -eq 0 ]]; then
  mapfile -t roles < <(cd "$ROOT" && ls -d */ 2>/dev/null | tr -d /)
fi

source /opt/nostromo/runtime/env.sh

overall=0
for role in "${roles[@]}"; do
  wt="$ROOT/$role"
  echo "================ $role  ($wt)"
  [[ -d "$wt" ]] || { echo "  MISSING worktree"; overall=1; continue; }
  cd "$wt" || { overall=1; continue; }

  dirty=$(git status --porcelain | wc -l)
  printf '  git status          %s\n' \
    "$([[ $dirty -eq 0 ]] && echo 'clean' || echo "$dirty uncommitted path(s) — INVESTIGATE")"
  [[ $dirty -eq 0 ]] || overall=1

  if [[ ! -x .venv/bin/python ]]; then
    echo "  creating .venv (python 3.12)"
    uv venv --python 3.12 --quiet .venv || { echo "  venv FAILED"; overall=1; continue; }
  fi
  echo "  installing (editable package + pinned test requirements)"
  if ! VIRTUAL_ENV="$wt/.venv" uv pip install --quiet -e . -c ci-constraints.txt \
       && VIRTUAL_ENV="$wt/.venv" uv pip install --quiet -r tests/requirements.txt -c ci-constraints.txt; then
    echo "  install FAILED"; overall=1; continue
  fi
  printf '  python              %s\n' "$(.venv/bin/python --version)"

  echo "  running the repository's own gate: scripts/dev/run_regression_tests.sh"
  start=$(date +%s)
  if PATH="$wt/.venv/bin:$PATH" bash scripts/dev/run_regression_tests.sh >/tmp/reg-$role.log 2>&1; then
    printf '  GATE PASSED         %ss  (%s)\n' "$(( $(date +%s) - start ))" \
      "$(grep -oE '[0-9]+ passed[^)]*' /tmp/reg-$role.log | tail -1)"
  else
    printf '  GATE FAILED         %ss — see /tmp/reg-%s.log\n' "$(( $(date +%s) - start ))" "$role"
    grep -E "^(FAILED|ERROR)|failed," /tmp/reg-$role.log | tail -5 | sed 's/^/    /'
    overall=1
  fi
done

echo
[[ $overall -eq 0 ]] && echo "every worktree bootstrapped and passed the repository's gate" \
                     || echo "AT LEAST ONE WORKTREE DID NOT PASS" >&2
exit $overall
