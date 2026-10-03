# Relay upgrade 0cc63fe3 -> fccc07eb

**Date.** 2026-10-03, 12:48 UTC. Second run of `bin/upgrade.sh`. Pin committed in `deef0b5`.

| | before | after |
|---|---|---|
| commit | `0cc63fe3` (2026-09-23) | `fccc07eb` (2026-09-29) |
| image index | `sha256:fc046cc6…` | `sha256:0e44ea54…` (arm64 child `sha256:3942a300…`) |
| schema | migration 48 | migration 53 |
| compose | `c654d9d3…` | unchanged |

## Why this commit, not `main`

Buzz Desktop 0.5.26 was installed the day before and expects a newer relay than `0cc63fe3`. `main` on
the day was `33f54de2`, hours old, carrying migrations 0049–0055. `fccc07eb` is the squash-merge of the
0.5.26 release onto `main` — tree-identical to tag `desktop-v0.5.26` (`2b4b138d`, whose own CI built no
image) — so it is the relay that Desktop release was cut with. ghcr has no per-commit tags: the digest is
`RELEASE_DIGEST` in upstream's Docker image run 36640106404 (the run for `fccc07eb` on `main`), and
`resolve-pin.sh --expect fccc07eb…` confirmed the arm64 child's revision label before anything was
written.

**Crew compatibility, read before the upgrade.** Several of the 56 commits tighten authentication
(NIP-FI, #7224, #7264; Blossom kind-24242 hardening, #7288). All of it is gated on `BUZZ_NIP_FI_MODE`,
which defaults to `off` and is unset here; outside its strict mode Blossom auth keeps the one-hour
window. So the crew's `buzz` binaries, still at `0cc63fe3`, were left alone — the Spark was running
SquadOps cycles, and a rebuild is a minute of heavy CPU there. Rebuild them when it is idle.

## Rehearsal, on the Mac, against the set the upgrade itself took

Backup `20261003T124800Z`, copied off-host, checksums verified. `upgrade.sh` gated the install on the
rehearsal; its output was not kept by that run, so it was re-run against the same set afterwards:

```text
restored: schema 48, events=1500 channels=12 members=8 audit=24185
ok: the old relay accepts the restored copy, so this set is a working rollback point
schema now 53, took 0.4s including container start
ok: events=1500 channels=12 members=8 audit=24185 unchanged
audit_log by hash_version: v1=12611 v2=11574
no — error: migration error: migration 49 was previously applied but is missing in the resolved migrations
```

Rollback is therefore the old pin plus a restore of `20261003T124800Z` (README, "Upgrade and rollback").
Anything written after the upgrade is lost.

## After install

- `probe.sh`: every check passed — liveness, readiness, migrations complete, secrets 600, relay and pair
  on the pinned image, certificate, NIP-11, wss upgrade from the Mac and from the Spark, 443 bound to the
  tailnet address only, funnel off, plaintext and LAN refused.
- Every running crew identity re-authenticated (NIP-42 auth successful for Mother, Ripley, Dallas, Parker
  and Brett), and so did the owner's Desktop. Every crew NIP-05 handle resolves.
- The recreated containers started fresh log files, which ended the damage the 2026-09-28 power cut had
  left in the relay's docker log: `buzzctl logs relay --since 10m` reads again. `rollout.sh` keeps its
  short-tail check (`4d77a38`), which does not depend on that.
