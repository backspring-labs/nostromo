#!/usr/bin/env bash
# Install and start nostromo-budget-watch. Runs ON the Spark, AS root — once; later changes to the
# watcher itself arrive with push-repo.sh and take effect on `systemctl restart nostromo-budget-watch`.
#
# Touches nothing else: no crew unit is restarted, unlike install-units.sh.
set -euo pipefail
REPO="${NOSTROMO_REPO:-/opt/nostromo/nostromo-src}"
SRC="$REPO/infrastructure/spark/systemd/nostromo-budget-watch.service"
DST=/etc/systemd/system/nostromo-budget-watch.service
die() { echo "install-budget-watch: $*" >&2; exit 1; }
[[ "$(id -u)" == 0 ]] || die "run as root: sudo $0"
[[ -r "$SRC" ]] || die "missing $SRC — run push-repo.sh from the Mac"
[[ -x "$REPO/infrastructure/spark/bin/budget-watch" ]] || die "budget-watch is missing or not executable"
getent group systemd-journal >/dev/null || die "no systemd-journal group on this host"

install -d -m 755 -o nostromo -g nostromo /opt/nostromo/state
install -d -m 755 -o nostromo -g nostromo /opt/nostromo/state/budget
install -m 644 "$SRC" "$DST"
systemctl daemon-reload
systemctl enable nostromo-budget-watch
systemctl restart nostromo-budget-watch
sleep 3
echo "nostromo-budget-watch: $(systemctl is-active nostromo-budget-watch)"
journalctl -u nostromo-budget-watch -n 10 --no-pager -o cat
