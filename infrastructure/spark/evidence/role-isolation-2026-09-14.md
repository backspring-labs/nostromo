# One Unix account per crew role

**Date.** 2026-09-14. **Host.** `spark`. Amends Bootstrap Plan §11 and closes the residual
recorded in `wp4-crew-account-and-runtime-2026-09-13.md`.

## Why this was brought forward

WP-4 gave the crew a single contained account, which stopped agents reaching the **owner's**
credentials. It left agent-to-agent isolation open, and that was deferred to WP-7 on the grounds
that only GitHub tokens were at stake.

WP-5 changes the stakes: it mints seven Buzz identities — the credentials that let one agent speak
**as another** in the crew's channels. Creating those into a shared account would have written seven
keys somewhere every agent could read, then required a migration.

Under one shared account, an agent could read any other role's App private key and mint that role's
token, read any other role's provider key and spend its budget, read any other role's Buzz key and
post as that crew member, inspect or kill another agent's process, and edit the permission profiles
and credential helpers meant to constrain it. **Every per-role control was advisory** — a prompt
promise wearing the costume of a deterministic control.

It matters beyond security. If Parker can act as Dallas then *"Dallas reviewed this"* stops being
evidence of independent review, and Operating Model's measurement apparatus rests on attribution
being real.

## Shape

| | |
|---|---|
| Accounts | `mother` `ash` `ripley` `dallas` `parker` `brett` `lambert`, uid 1002–1008 |
| Naming | **no prefix.** The GitHub Apps need `nostromo-` because they live in a global namespace; Unix accounts on one box do not, and the prefix costs width in every `ls`, `ps` and log line |
| Affiliation | secondary membership of the existing `nostromo` group, which grants **read of the shared runtime and nothing else** |
| Homes | **700, not 750.** With a shared group, 750 would let every role read every other role's home and reintroduce the exact problem being solved |
| Secrets | `~/.config/nostromo/secrets` per role, 700, owned by that role |
| Escalation | none in `sudo`, `docker` or `adm`; the script refuses to leave a role in any of them |
| Supervisor | `nostromo` (uid 1001) owns `/opt/nostromo` and runs the launcher. It is the trusted component by construction: it holds every key in order to hand each role only its own |

Also fixed: the supervisor's `secrets` directory was **755**. The keys inside were 600, so nothing
was readable, but the listing was open.

## Verified from inside each account

`verify-role-isolation.sh` ssh's into all seven and runs eleven checks **as that role**, because
that is the position an agent occupies. Root simulating it with `sudo -u` is a weaker claim — and
an earlier version of the owner-boundary check reported a holding boundary as eight failures by
comparing a result against the wrong string, so every check here names exactly what it expects and
rejects a malformed expectation rather than inverting silently.

```text
mother ash ripley dallas parker brett lambert   — 11 checks each, 77 total, all PASS

  cannot read another named role's home        cannot reach the docker socket
  cannot read another named role's secrets     cannot sudo
  cannot read the supervisor's secrets         cannot write the shared runtime
  cannot read the owner's home                 can write its own home and secret directory
                                               can READ the shared runtime, can reach Ollama
```

The "another role" in each run is a **different named role**, not a placeholder, so the comparison
is real in both directions.

## What this does not close

- An agent can do anything **its own role** permits. That is the design.
- **Network access is unrestricted** — any role can reach any host.
- **The launcher must be trusted.** It holds every key by necessity.
- A compromised Spark still yields the ability to act as any role, bounded by the controls enforced
  **off-box**: branch namespaces and the crew check at GitHub, spend caps at the providers, and
  membership and channel gates on the relay. Those survive it.

## Next

Migrate each role's App private key and worktree from the supervisor to its owner, and re-point the
per-worktree credential helpers. No password needed; it is a move and a chown.
