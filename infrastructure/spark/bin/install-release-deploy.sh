#!/usr/bin/env bash
# One authenticated step: put the Spark on release deploys, and retire the password-free helper.
# Runs ON the Spark, AS root, from a release the supervisor has already staged:
#
#   ssh nostromo@spark 'python3 -I - stage' < infrastructure/spark/bin/nostromo-release.py   (from the Mac;
#     before adoption there is no current to run it from)
#   sudo bash /opt/nostromo/releases/<sha>/infrastructure/spark/bin/install-release-deploy.sh
#
# Afterwards everything reads through /opt/nostromo/current, and nostromo-release.py deploys a
# merged commit with no sudo (docs/runbooks/deployment.md). What it changes:
#   - /opt/nostromo/current -> this release; /opt/nostromo/nostromo-src becomes a link to it (the old
#     git working tree is kept under /opt/nostromo/backups).
#   - /usr/local/lib/nostromo, /usr/local/bin/campaignctl and /usr/local/share/nostromo become
#     root-owned links into current, instead of root-owned copies.
#   - 48-nostromo-release.rules lets the supervisor restart the units that run release code.
#   - nostromo@.service is reinstalled from this release.
#   - /usr/local/sbin/nostromo-deploy, its sudoers rule, config and state move to a backup.
# Root runs nothing from the release except this script, which the owner reads before running.
set -euo pipefail
die() { echo "install-release-deploy: $*" >&2; exit 1; }
[[ $(id -u) == 0 ]] || die "run as root (sudo bash $0)"

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
SHA="$(basename "$HERE")"
[[ "$(dirname "$HERE")" == /opt/nostromo/releases && "$SHA" =~ ^[0-9a-f]{40}$ ]] \
  || die "run this from a staged release under /opt/nostromo/releases, not a checkout"
[[ "$(stat -c %U "$HERE")" == nostromo ]] || die "$HERE is not owned by the supervisor"
[[ -z "$(find "$HERE" -perm /022 -not -type l -print -quit)" ]] || die "$HERE is group- or other-writable"
[[ -f "$HERE/RELEASE.json" ]] || die "$HERE has no RELEASE.json; stage it with nostromo-release.py"

BIN="$HERE/infrastructure/spark/bin"
CUR=/opt/nostromo/current
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
BACKUP="/var/backups/nostromo-release-adopt-$STAMP"
install -d -m 700 "$BACKUP"
DAEMONS=(nostromo-campaign-broker.service nostromo-campaign-watch.service nostromo-budget-watch.service)
TIMERS=(nostromo-campaign-window.timer nostromo-campaign-advance.timer nostromo-campaign-launch.timer
        nostromo-campaign-review@ripley.timer nostromo-campaign-review@dallas.timer)
ENTRYPOINTS=(campaign-broker.py campaign-watch.py campaign-window.py campaign-window-check.py
             campaign-review.py campaign-advance.py campaign-launch.py)
RUNBOOKS=(campaign-control.md shared-inference.md deployment.md)

echo "== release $SHA ($(python3 -I -c 'import json,sys; print(json.load(open(sys.argv[1]))["subject"])' "$HERE/RELEASE.json"))"
echo "== backup  $BACKUP"

# 1. Drain: pause the campaign timers, wait for any running worker, then stop the daemons.
PAUSED=()
for t in "${TIMERS[@]}"; do
  if systemctl is-active --quiet "$t"; then systemctl stop "$t"; PAUSED+=("$t"); fi
done
# A running oneshot worker is "activating", which `is-active --quiet` reports as not active.
running() { [[ "$(systemctl is-active "$1" || true)" =~ ^(active|activating|deactivating|reloading)$ ]]; }
for _ in $(seq 150); do
  busy=0
  for t in "${TIMERS[@]}"; do if running "${t%.timer}.service"; then busy=1; fi; done
  if [[ $busy == 0 ]]; then break; fi
  sleep 2
done
if [[ $busy == 1 ]]; then
  for t in "${PAUSED[@]}"; do systemctl start "$t"; done
  die "a campaign worker is still running after 300 s; nothing changed. Retry later"
fi
systemctl stop "${DAEMONS[@]}"
echo "== drained (paused: ${PAUSED[*]:-none})"

# 2. One tree: current -> this release, and nostromo-src -> current.
[[ -e $CUR && ! -L $CUR ]] && die "$CUR exists and is not a link"
ln -sfn "releases/$SHA" "$CUR" && chown -h nostromo:nostromo "$CUR"
if [[ -d /opt/nostromo/nostromo-src && ! -L /opt/nostromo/nostromo-src ]]; then
  mv /opt/nostromo/nostromo-src "/opt/nostromo/backups/nostromo-src-pre-release-$STAMP"
fi
ln -sfn current /opt/nostromo/nostromo-src && chown -h nostromo:nostromo /opt/nostromo/nostromo-src

# 3. /usr/local: root-owned directories of links into current, replacing root-owned copies.
NEW=/usr/local/lib/nostromo.new
rm -rf "$NEW" && install -d -m 755 "$NEW"
ln -s "$CUR/runtime/campaigns" "$NEW/campaigns"
for e in "${ENTRYPOINTS[@]}"; do ln -s "$CUR/infrastructure/spark/bin/$e" "$NEW/$e"; done
[[ -d /usr/local/lib/nostromo ]] && mv /usr/local/lib/nostromo "$BACKUP/usr-local-lib-nostromo"
mv "$NEW" /usr/local/lib/nostromo
[[ -e /usr/local/bin/campaignctl ]] && mv /usr/local/bin/campaignctl "$BACKUP/campaignctl"
ln -s "$CUR/infrastructure/spark/bin/campaignctl" /usr/local/bin/campaignctl
NEW=/usr/local/share/nostromo.new
rm -rf "$NEW" && install -d -m 755 "$NEW"
for r in "${RUNBOOKS[@]}"; do ln -s "$CUR/docs/runbooks/$r" "$NEW/$r"; done
for role in ripley dallas; do ln -s "$CUR/crew/personas/$role.md" "$NEW/campaign-$role.md"; done
[[ -d /usr/local/share/nostromo ]] && mv /usr/local/share/nostromo "$BACKUP/usr-local-share-nostromo"
mv "$NEW" /usr/local/share/nostromo
echo "== linked /usr/local/lib/nostromo, /usr/local/bin/campaignctl, /usr/local/share/nostromo into $CUR"

# 4. Polkit for the supervisor's restarts, and the crew unit from this release.
install -m 644 "$HERE/infrastructure/spark/systemd/48-nostromo-release.rules" /etc/polkit-1/rules.d/
cp -p /etc/systemd/system/nostromo@.service "$BACKUP/" 2>/dev/null || true
install -m 644 "$HERE/infrastructure/spark/systemd/nostromo@.service" /etc/systemd/system/nostromo@.service
systemctl daemon-reload

# 5. Retire the password-free root helper.
if [[ -e /etc/sudoers.d/nostromo-deploy ]]; then
  mv /etc/sudoers.d/nostromo-deploy "$BACKUP/sudoers-nostromo-deploy"
  visudo -c >/dev/null || die "visudo -c failed after removing the rule; inspect /etc/sudoers.d"
fi
for p in /usr/local/sbin/nostromo-deploy /etc/nostromo/deploy.json /var/lib/nostromo-deploy; do
  [[ -e $p ]] && mv "$p" "$BACKUP/$(basename "$p")"
done
echo "== retired nostromo-deploy and its sudoers rule"

# 6. Start, check, resume.
systemctl start "${DAEMONS[@]}"
for t in "${PAUSED[@]}"; do systemctl start "$t"; done
sleep 5
# Report, don't abort: a unit that failed to start is what the status below is for.
echo "== units: $(systemctl is-active "${DAEMONS[@]}" "${TIMERS[@]}" | paste -sd' ' || true)"
echo
runuser -u nostromo -- python3 -I "$BIN/nostromo-release.py" status
echo
echo "Done. Crew harnesses still run the persona they launched with: restart them from the Mac with"
echo "  infrastructure/spark/bin/rollout.sh"
echo "To undo: the previous files are in $BACKUP."
