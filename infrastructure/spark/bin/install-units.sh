#!/usr/bin/env bash
# Install the Nostromo systemd template and enable roles. Runs ON the Spark, AS root.
#
# Usage:  install-units.sh [role ...]        default: every role with a launch adapter
#         install-units.sh --dry-run [role ...]
set -euo pipefail

REPO="${NOSTROMO_REPO:-/opt/nostromo/nostromo-src}"
UNIT_SRC="$REPO/infrastructure/spark/systemd/nostromo@.service"
UNIT_DST=/etc/systemd/system/nostromo@.service

die() { echo "install-units: $*" >&2; exit 1; }
[[ "$(id -u)" == 0 ]] || die "must run as root (systemd unit installation and role log dirs)"
[[ -r "$UNIT_SRC" ]] || die "missing $UNIT_SRC — run push-repo.sh from the Mac"

DRY=""; [[ "${1:-}" == "--dry-run" ]] && { DRY=1; shift; }

# A role is installable when it has an adapter. Today those are explicit per role; §13.9 replaces
# them with one generic launcher, deliberately only after Mother and Brett both work.
roles=("$@")
if [[ ${#roles[@]} -eq 0 ]]; then
  for f in "$REPO"/infrastructure/spark/bin/launch-*.sh; do
    [[ -e "$f" ]] || continue
    r="$(basename "$f")"; r="${r#launch-}"; r="${r%.sh}"
    roles+=("$r")
  done
fi
[[ ${#roles[@]} -gt 0 ]] || die "no launch-<role>.sh adapters found in $REPO"

echo "unit:  $UNIT_SRC"
echo "roles: ${roles[*]}"
echo

for role in "${roles[@]}"; do
  id -u "$role" >/dev/null 2>&1 || die "no such user: $role (run create-role-accounts.sh first)"
  [[ -x "$REPO/infrastructure/spark/bin/launch-$role.sh" ]] \
    || die "no adapter for $role at $REPO/infrastructure/spark/bin/launch-$role.sh"
  # Asserted by the adapter too, but a unit that fails at boot is worse than a refusal now.
  [[ -r "/home/$role/.config/nostromo/secrets/buzz.key" ]] \
    || die "$role has no key at /home/$role/.config/nostromo/secrets/buzz.key"
  install -d -m 755 -o nostromo -g nostromo /opt/nostromo/logs
  install -d -m 2750 -o "$role" -g nostromo "/opt/nostromo/logs/$role"
  echo "  $role: user ok, adapter ok, key ok, log dir ok"
done
echo

if [[ -n "$DRY" ]]; then
  echo "--dry-run: nothing installed"
  exit 0
fi

install -m 644 "$UNIT_SRC" "$UNIT_DST"
systemctl daemon-reload
echo "installed $UNIT_DST"
echo

for role in "${roles[@]}"; do
  # A role already running by hand would make the adapter's own single-instance guard fail the
  # unit. Stop the hand-launched one first; it is exactly what the unit replaces.
  if pgrep -u "$role" -x buzz-acp >/dev/null 2>&1; then
    echo "  $role: stopping hand-launched buzz-acp (pid $(pgrep -u "$role" -x buzz-acp | tr '\n' ' '))"
    pkill -u "$role" -x buzz-acp || true
    sleep 2
  fi
  systemctl enable --now "nostromo@$role"
  sleep 3
  printf '  %s: %s\n' "$role" "$(systemctl is-active "nostromo@$role")"
done

echo
echo "  systemctl status nostromo@<role>"
echo "  journalctl -u nostromo@<role> -f"
