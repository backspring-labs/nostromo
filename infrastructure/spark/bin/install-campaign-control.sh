#!/usr/bin/env bash
# Reviewed root step, ON the Spark. Never installs or grants a sudoers exception to an agent.
# Usage: sudo bash install-campaign-control.sh /path/to/nostromo /path/to/owner-staging
set -euo pipefail
REPO="${1:?usage: install-campaign-control.sh REPO STAGING}"
STAGING="${2:?usage: install-campaign-control.sh REPO STAGING}"
[[ $(id -u) == 0 ]] || { echo "run as root; no changes made" >&2; exit 1; }
[[ -f "$STAGING/config.json" ]] || { echo "prepare-campaign-auth.py must succeed first" >&2; exit 1; }
getent group nostromo >/dev/null
OWNER_USER="$(python3 - "$STAGING/config.json" <<'PY'
import json, pathlib, pwd, sys
c=json.loads(pathlib.Path(sys.argv[1]).read_text())
owners=[int(uid) for uid,role in c['callers'].items() if role=='owner']
if len(owners)!=1 or owners[0]<1000:
    raise SystemExit('expected exactly one non-root owner UID')
print(pwd.getpwuid(owners[0]).pw_name)
PY
)"
# The owner is a socket caller too. A fresh login picks up this supplementary group.
usermod -aG nostromo "$OWNER_USER"
if ! id nostromo-broker >/dev/null 2>&1; then
  useradd --system --no-create-home --shell /usr/sbin/nologin --gid nostromo nostromo-broker
fi
for forbidden in sudo docker adm; do
  if id -nG nostromo-broker | tr ' ' '\n' | grep -qx "$forbidden"; then
    echo "refusing broker with privileged group $forbidden" >&2; exit 1
  fi
done
install -d -m 755 /usr/local/lib/nostromo /usr/local/lib/nostromo/campaigns /etc/nostromo
install -d -m 700 -o nostromo-broker -g nostromo /etc/nostromo/secrets
install -d -m 755 -o nostromo-broker -g nostromo /var/lib/nostromo-campaign-broker
for source in "$REPO"/runtime/campaigns/*.py; do
  install -m 644 -o root -g root "$source" /usr/local/lib/nostromo/campaigns/
done
install -m 644 "$REPO/infrastructure/buzz/bin/nostr_keys.py" /usr/local/lib/nostromo/campaigns/nostr_keys.py
for name in campaign-broker.py campaign-watch.py campaign-window.py campaign-window-check.py; do
  install -m 755 "$REPO/infrastructure/spark/bin/$name" /usr/local/lib/nostromo/
done
install -m 755 "$REPO/infrastructure/spark/bin/campaignctl" /usr/local/bin/campaignctl
install -d -m 755 /usr/local/share/nostromo
install -m 644 "$REPO/docs/runbooks/campaign-control.md" /usr/local/share/nostromo/campaign-control.md
for role in control review read; do
  if [[ -f "$STAGING/$role.pem" ]]; then
    install -m 600 -o nostromo-broker -g nostromo "$STAGING/$role.pem" "/etc/nostromo/secrets/campaign-$role.pem"
  fi
  [[ -s "/etc/nostromo/secrets/campaign-$role.pem" ]] || { echo "missing key for $role" >&2; exit 1; }
done
python3 - "$STAGING/config.json" <<'PY'
import json, pathlib, sys
c=json.loads(pathlib.Path(sys.argv[1]).read_text())
for principal, client in c['clients'].items():
    client['key_file']='/etc/nostromo/secrets/campaign-'+principal+'.pem'
p=pathlib.Path('/etc/nostromo/campaign-broker.json')
p.write_text(json.dumps(c,indent=2)+'\n')
p.chmod(0o644)
PY
install -m 644 "$REPO/infrastructure/spark/systemd/50-nostromo-campaign-window.rules" /etc/polkit-1/rules.d/
for name in nostromo-campaign-broker.service nostromo-campaign-watch.service nostromo-campaign-window.service nostromo-campaign-window.timer; do
  install -m 644 "$REPO/infrastructure/spark/systemd/$name" /etc/systemd/system/
done
for role in mother brett; do
  install -d -m 755 "/etc/systemd/system/nostromo@$role.service.d"
  cat > "/etc/systemd/system/nostromo@$role.service.d/20-campaign-window.conf" <<'UNIT'
[Service]
ExecCondition=/usr/bin/python3 -I /usr/local/lib/nostromo/campaign-window-check.py
UNIT
done
systemctl daemon-reload
systemctl enable --now nostromo-campaign-broker.service nostromo-campaign-window.timer nostromo-campaign-watch.service
systemctl is-active nostromo-campaign-broker.service nostromo-campaign-window.timer nostromo-campaign-watch.service
echo "Installed. Existing crew services need no restart; the startup condition applies at their next start."
echo "Verify the socket's role refusals before approving any definition or starting a campaign."
