#!/usr/bin/env bash
# Re-render and publish the crew's channel canvases, as Mother on the Spark. From the Mac.
#
#   sync-canvases.sh                  publish every canvas that changed
#   sync-canvases.sh --dry-run        print the pages; publish nothing
#   sync-canvases.sh --only nostromo  one canvas
#
# deploy-spark.sh runs this after every deploy. Run it by hand after a change it can't see: a campaign
# opening or closing, a role paused or restarted, a Spark mode change.
set -euo pipefail
# Quote arguments only when there are some: printf '%q ' with none emits '', an empty argument.
ARGS=""
[[ $# -gt 0 ]] && ARGS=" $(printf '%q ' "$@")"
exec ssh "${NOSTROMO_MOTHER:-mother@spark}" "python3 -I /opt/nostromo/current/infrastructure/buzz/bin/sync-canvases.py$ARGS"
