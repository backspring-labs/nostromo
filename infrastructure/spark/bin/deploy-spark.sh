#!/usr/bin/env bash
# Deploy Nostromo to the Spark: merged main by default. From the Mac, or any session holding the
# supervisor's SSH key. Replaces push-repo.sh: the Spark now fetches GitHub main itself, so nothing
# local travels and an unmerged branch cannot reach the crew by accident (docs/runbooks/deployment.md).
#
#   deploy-spark.sh                         deploy the head of GitHub main
#   deploy-spark.sh deploy <commit>         an earlier commit on main
#   deploy-spark.sh status | rollback | stage [<commit>]
#   deploy-spark.sh deploy <commit> --allow-unmerged "<reason>"   an owner-approved trial only
#
# Campaign daemons restart as part of a deploy; crew harnesses do not. Restart those with rollout.sh.
set -euo pipefail
TARGET="${NOSTROMO_SUPERVISOR:-nostromo@spark}"
[[ $# -gt 0 ]] || set -- deploy
ssh "$TARGET" "python3 -I /opt/nostromo/current/infrastructure/spark/bin/nostromo-release.py $(printf '%q ' "$@")"
# A release changes what the crew's canvases say is live. Best effort: the deploy has already
# succeeded, and a stale canvas is not a reason to report it as failed.
if [[ "$1" == deploy || "$1" == rollback ]]; then
  "$(dirname "${BASH_SOURCE[0]}")/../../buzz/bin/sync-canvases.sh" \
    || echo "deploy-spark: deployed, but a canvas did not sync; run sync-canvases.sh" >&2
fi
