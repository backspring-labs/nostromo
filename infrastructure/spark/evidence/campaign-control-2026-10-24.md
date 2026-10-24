# Campaign adapter preparation — 2026-10-24

Owner authorized separate scoped identities, the tested broker/watcher deployment, and one
local `group_run` diagnostic bounded to one calibration cycle. No increments, retries, paid
dispatches, or automatic reserved owner decisions are authorized by that commissioning request.

Observed on Spark:

- `campaign-operations`, `campaign-review`, and `campaign-evidence` were provisioned as separate
  private-key JWT service clients in `squadops-local`. Their roles are respectively
  `campaign-supervisor`; `campaign-supervisor` plus `operator`; and `campaign-triage`.
- Each client authenticated and successfully read `/api/v1/projects` through the deployed API.
  The provisioning code checked that no service account had the realm `admin` role.
- Host-local Keycloak transport uses `127.0.0.1:8180` with `Host: spark:8180`, preserving the
  runtime's configured public issuer. Non-loopback HTTP requests receive 403 under the realm's
  existing SSL policy. No realm or API authentication policy was changed.
- Owner-only signing keys and public broker configuration are staged in
  `/home/jladd/.config/nostromo/campaign-provision`. No keys or tokens are recorded here.
- The Linux `SO_PEERCRED` socket integration test passed, including caller spoofing,
  unauthorized gate write, unapproved definition, and unadmitted UID refusals. Its external
  API fixture recorded zero calls for the refused actions.
- Mother, Ripley, and Dallas have supplementary `nostromo` group membership for socket access.
- systemd unit validation returned success; it also reported unrelated pre-existing unit files
  unreadable by the owner (`dgx-dashboard-admin`, `squadops-docker-prune`, `squadops-backup`).

**Pending:** root installation, installed service health and live role checks, and the single
commissioning diagnostic. `sudo -n true` requires a password. No attempt was made to bypass it
through Docker or to grant crew sudo. No campaign was launched during preparation.

Runbook: [Campaign control from Buzz](../../../docs/runbooks/campaign-control.md).

## Installed boundary checks

After the owner's interactive installation, broker, watcher, and guard timer reported active.
The owner was in the socket's `nostromo` group. The installed socket was broker-owned, group
`nostromo`, mode 0660; the approval database was mode 0600; the secrets directory was mode 0700.

Actual SSH role checks passed: Mother could not submit a gate; Ripley, Dallas, and Brett could
not issue campaign operations; Ripley could not submit an unsigned gate decision. No gate
writes were made by these probes. The deployed squad profile and all six squad agents were
confirmed on TensorFold, with the 27B model loaded and the box reporting quiet.

The pre-start packet check caught a broker route defect: its `log` read used `/log`, whereas
the deployed API exposes `/control-log`. The correction maps both the direct log read and the
watcher's packet read to that route, with a regression test. The installer now restarts active
broker/watcher units so copied Python changes actually load on an upgrade.

The single diagnostic was created and remains **draft**, with zero cycles started. Its
definition and coordination record are in the broker and Buzz, not this GitHub repository.
Root reinstallation of this correction and an installed packet check are required before start;
the existing approval and draft must be reused. Noninteractive sudo still requires a password.
