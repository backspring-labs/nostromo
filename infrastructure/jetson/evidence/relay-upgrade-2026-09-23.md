# Relay upgrade c045321a -> 0cc63fe3

**Date.** 2026-09-23, 19:39–19:41 UTC. First run of `bin/upgrade.sh`. Pin committed in `becc40c`.

| | before | after |
|---|---|---|
| commit | `c045321a` (2026-09-08) | `0cc63fe3` (2026-09-23) |
| image index | `sha256:496c38cc…` | `sha256:fc046cc6…` |
| schema | migration 44 | migration 48 |
| MinIO | Docker Hub | Quay, same digests |

## Rehearsal, on the Mac, against the set the upgrade itself took

Backup `20260923T193949Z`, copied off-host, checksums verified, then:

```text
restored: schema 44, events=1223 channels=4 members=8 audit=12611
ok: the old relay accepts the restored copy, so this set is a working rollback point
schema now 48, took 0.4s including container start
ok: events=1223 channels=4 members=8 audit=12611 unchanged
audit_log by hash_version: v1=12611
no — error: migration error: migration 45 was previously applied but is missing in the resolved migrations
```

The last line is the rollback constraint, measured: after this upgrade the old relay does not start,
so going back is the old pin plus a restore of `20260923T193949Z` (README, "Upgrade and rollback").
An earlier rehearsal against `20260923T185238Z` took 6.2 s; the difference is image pull, not migration.

## After install

- All 18 probes pass, including the new "runs the pinned image" (`relay, pair @sha256:fc046cc6bfe8`).
- NIP-11 now advertises `read_state_snapshot`, the capability Desktop 0.5.24 gates #7572 on.
- Within five minutes every running identity had re-authenticated over NIP-42: the owner (Desktop)
  and mother, ripley, dallas, parker, brett. Ash and Lambert are not running.

## Warnings at startup, both benign

- Three `transport drop` warnings from the git object-store conformance probe, which races 32
  writers for 3 rounds by design. It reported `A3 conformance probe passed`, `transport_drops: 3`.
- `NIP-43 membership reconciliation failed … community write fenced` for the two communities
  deleted on 2026-09-13 (`nano.tailc69e7d.ts.net`, `buzz.backspring.xyz`). The deletion fence doing
  its job; the live community reconciled. Whether this predates the upgrade is unknown — the old
  container's logs went with it. Worth an upstream note: reconciliation should skip fenced communities.
