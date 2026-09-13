# Implementation Deviation Log

Every meaningful deviation between NOSTROMO-0001, NOSTROMO-PLAN-0001, and what tooling actually allows is recorded here (NOSTROMO-PLAN-0001 §29). Only a true architecture contradiction revises the specification; everything else is logged and, where needed, approved.

## Entry template

```text
ID:                    DEV-NNN
Date:
Spec/plan reference:
Expected:
Actual tooling constraint:
Chosen workaround:
Security/cost impact:
Temporary or permanent:
Owner approval:
Revisit trigger:
```

## Entries

```text
ID:                    DEV-001
Date:                  2026-09-08
Spec/plan reference:   NOSTROMO-0001 §20; NOSTROMO-PLAN-0001 §9.6
Expected:              wss:// on nano.tailc69e7d.ts.net with Tailscale Serve terminating TLS
Actual tooling constraint: HTTPS certificates are not enabled for the tailnet (CertDomains null), and
                       tailscale serve needs root or the operator setting, which needs sudo; sudo on the
                       Jetson prompts for a password that this session cannot supply.
Chosen workaround:     Relay published on ws://nano.tailc69e7d.ts.net:3000, bound to the Tailscale address
                       and loopback only. Plan §9.6 allows a private ws:// bootstrap.
Security/cost impact:  Traffic between tailnet nodes is already WireGuard-encrypted; nothing is reachable
                       from the LAN or the public Internet. No cost.
Temporary or permanent: Temporary.
Owner approval:        Recorded for review; the two owner actions are listed in infrastructure/jetson/README.md, "TLS".
Revisit trigger:       HTTPS certificates enabled and operator set; then Serve plus the five buzz.env lines.
Resolved:              2026-09-08, same day. Owner enabled HTTPS certificates and set the operator; Serve
                       terminates TLS on 443 (tailnet only), buzz.env advertises wss://, and the plaintext
                       tailnet binding was removed. Kept for the record.
```

```text
ID:                    DEV-002
Date:                  2026-09-08
Spec/plan reference:   NOSTROMO-PLAN-0001 §9.5 (owner pubkey listed as a WP-2 input); owner-identity hold of 2026-09-07
Expected:              RELAY_OWNER_PUBKEY set to the owner's real pubkey
Actual tooling constraint: buzz-relay at c045321a refuses to start in closed mode without RELAY_OWNER_PUBKEY
                       (crates/buzz-relay/src/main.rs, "RELAY_OWNER_PUBKEY required when
                       BUZZ_REQUIRE_RELAY_MEMBERSHIP=true"), and the owner keypair is on hold until WP-3.
Chosen workaround:     A placeholder owner pubkey generated on the Jetson with buzz-admin generate-key, its
                       secret discarded at generation. Recorded in buzz.env and owner.placeholder.pubkey.
Security/cost impact:  Nobody can administer the relay until WP-3; the relay is closed and inert. Opening the
                       relay instead was rejected. The swap procedure is in infrastructure/jetson/README.md,
                       "Owner identity": the relay demotes the placeholder to admin, then it is removed.
Temporary or permanent: Temporary.
Owner approval:        Recorded for review.
Revisit trigger:       WP-3 mints the owner keypair.
```

```text
ID:                    DEV-003
Date:                  2026-09-08
Spec/plan reference:   NOSTROMO-PLAN-0001 §9.2, §9.3
Expected:              Use the upstream production bundle as shipped, overlays only
Actual tooling constraint: Upstream deploy/compose/run.sh hard-codes "-f compose.yml", so the Nostromo overlay
                       (port binding, env-file split, digest pins) cannot be loaded through it.
Chosen workaround:     infrastructure/jetson/bin/buzzctl wraps the same Compose invocations with both files and
                       both env files; run.sh is not deployed. compose.yml itself is fetched verbatim at the pin.
Security/cost impact:  None.
Temporary or permanent: Permanent unless upstream adds an overlay hook.
Owner approval:        Recorded for review.
Revisit trigger:       Upstream run.sh honours COMPOSE_FILE or an extra -f.
```

```text
ID:                    DEV-004
Date:                  2026-09-08
Spec/plan reference:   NOSTROMO-PLAN-0001 §9.4
Expected:              A chosen NVMe-backed directory for durable state
Actual tooling constraint: Upstream Compose declares named Docker volumes; switching to bind mounts would fork
                       upstream semantics.
Chosen workaround:     Named volumes stay, under the Docker data root, which is already on the NVMe
                       (/mnt/ssd/docker/volumes/buzz-prod_buzz-*-data). probe.sh fails if any mountpoint
                       leaves /mnt/ssd. Backups tar the volumes (backup.sh).
Security/cost impact:  None.
Temporary or permanent: Permanent.
Owner approval:        Recorded for review.
Revisit trigger:       Upstream moves to bind mounts.
```

```text
ID:                    DEV-006
Date:                  2026-09-13
Spec/plan reference:   NOSTROMO-PLAN-0001 §8.9; NOSTROMO-0002 §14, §45.4
Expected:              Four rulesets on squad-ops — a branch ruleset and a path ruleset per repo-writing
                       identity — so that "Ripley's namespace cannot carry implementation changes and
                       Parker's namespace cannot carry SIP changes" is enforced server-side.
Actual tooling constraint: GitHub refuses path restrictions on this repository, twice over. A branch-target
                       ruleset rejects the rule outright: `Invalid rule 'file_path_restriction'`. A
                       push-target ruleset, which is where that rule belongs, is refused with
                       `Source public repos cannot have push rules`. squad-ops is a public source
                       repository, so no path boundary of any kind is available to it.
Chosen workaround:     Branch-namespace rulesets only. `nostromo-parker-branches` and
                       `nostromo-ripley-branches` restrict creation, update and deletion on
                       `refs/heads/nostromo/<role>/**`, each bypassed by exactly one App. Probed with a
                       paired control: the role creates in its own namespace (201), the same role is
                       refused in the other's (422), and the owner is refused in a crew namespace (422).
Security/cost impact:  The half that is enforced is the more important half — attribution is guaranteed and
                       no agent can write into another's namespace or overwrite its work. The half that is
                       lost is role-scope containment within a namespace: nothing server-side stops Ripley
                       committing to `src/` on a Ripley branch. That returns to being a discipline, which
                       the record says drifts, and it is presently caught only by Dallas's review and by
                       the harness permission profile.
Temporary or permanent: Permanent while squad-ops is a public source repository.
Owner approval:        Recorded for review. The recommended remedy needs the owner's decision because it
                       changes squad-ops CI: a workflow that fails a pull request whose head branch is
                       `nostromo/<role>/**` and whose diff touches that role's forbidden paths, promoted to
                       a required status check. That converts the boundary back into a test, which is this
                       repository's own rule for anything discipline has been shown to miss, and it can
                       explain the violation where a ruleset can only reject a push. It passes trivially
                       for every non-crew pull request.
Revisit trigger:       The CI check landing; or squad-ops ceasing to be a public source repository; or
                       GitHub permitting push rules on public source repositories.
```

```text
ID:                    DEV-005
Date:                  2026-09-08
Spec/plan reference:   NOSTROMO-PLAN-0001 §9.8, §20 completion probe ("Jetson reboot preserves state")
Expected:              A reboot as part of WP-2 evidence
Actual tooling constraint: Reboot needs sudo, which prompts for a password on the Jetson.
Chosen workaround:     Proved a relay container restart and a full stack stop/start with stable identity.
                       The reboot is an owner action; probe.sh after it closes the item.
Security/cost impact:  None.
Temporary or permanent: Temporary.
Owner approval:        Recorded for review.
Revisit trigger:       First owner-initiated reboot of the Jetson.
Resolved:              2026-09-08. Owner rebooted the nano; tailscaled started before Docker, all four
                       containers returned under the restart policy with no restarts of their own, Serve
                       persisted, relay identity and the single community row unchanged, probe.sh 14 PASS.
```
