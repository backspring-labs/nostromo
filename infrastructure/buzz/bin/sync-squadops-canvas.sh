#!/usr/bin/env bash
# Re-render and publish the #squadops canvas, as Mother on the Spark. From the Mac.
#
#   sync-squadops-canvas.sh             publish if anything changed
#   sync-squadops-canvas.sh --dry-run   print the page; publish nothing
#
# deploy-spark.sh runs this after every deploy. Run it by hand after a change it can't see: a campaign
# opening or closing, or a Spark mode change.
set -euo pipefail
exec ssh "${NOSTROMO_MOTHER:-mother@spark}" \
  "python3 -I /opt/nostromo/current/infrastructure/buzz/bin/sync-squadops-canvas.py $(printf '%q ' "$@")"
