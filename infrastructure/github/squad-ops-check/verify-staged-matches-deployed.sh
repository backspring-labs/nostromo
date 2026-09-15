#!/usr/bin/env bash
# Assert the staged crew-check files are byte-identical to what is running on squad-ops.
#
# These files are a RECORD of what is deployed, not a place to edit. A local edit that never ships
# makes the record a lie — and it happens by accident, not intent: a repository-wide rename touched
# a comment in the boundaries file on 2026-09-15 and would have gone unnoticed.
#
# Changing behaviour means opening a pull request against squad-ops and re-staging afterwards.
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
fail=0
for rel in .github/nostromo-crew-boundaries.yml \
           .github/workflows/nostromo-crew-checks.yml \
           scripts/dev/check_nostromo_crew_pr.py; do
  local_file="$HERE/files/$rel"
  [[ -f "$local_file" ]] || { echo "MISSING locally: $rel"; fail=1; continue; }
  tmp="$(mktemp)"
  if ! gh api "repos/backspring-labs/squad-ops/contents/$rel" \
        -H "Accept: application/vnd.github.raw" > "$tmp" 2>/dev/null; then
    echo "COULD NOT FETCH $rel"; fail=1; rm -f "$tmp"; continue
  fi
  if diff -q "$tmp" "$local_file" >/dev/null; then
    printf '  identical  %s\n' "$rel"
  else
    printf '  DIFFERS    %s\n' "$rel"; diff "$tmp" "$local_file" | head -6; fail=1
  fi
  rm -f "$tmp"
done
[[ $fail == 0 ]] && echo "staged copies match squad-ops" || echo "STAGED COPIES DO NOT MATCH — re-stage or ship the change" >&2
exit $fail
