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
