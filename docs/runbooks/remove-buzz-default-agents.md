# Removing Buzz Desktop's default agents and channels

**Why the obvious approach fails.** Deleting the agents first does not work: they are recreated the
next time the `Welcome` channel is opened. `ensureWelcomeTeam(channelId, relayUrl)` fires for a
welcome channel, and `provisionWelcomeTeam` looks for an existing agent **per starter, scoped to the
relay URL** — finding none, it creates one. Because the lookup is relay-scoped, **every community
joined on this machine gets its own trio**, each with its own Nostr identity and a running
`buzz-acp` process.

As of 2026-09-13 this machine had **six** agents — Fizz, Honey and Pollen twice over, three bound to
`wss://buzz.backspring.xyz` and three to `wss://nostromo.backspring.xyz`, all running. Two of each
trio are `respond_to: allowlist`, not `owner-only`.

The Mac is meant to run no agents at all (NOSTROMO-0002 §35.4).

## The mechanism

`infrastructure/buzz/bin/purge-desktop-agents.sh` removes every provisioned agent — identities,
logs, retention databases — and leaves the inert personas. It refuses to run while Buzz Desktop is
open, because the app owns those files and will write over anything changed underneath it, and it
backs the whole agents directory up to `~/.nostromo/backups/buzz-desktop-agents/<stamp>` first.

```sh
infrastructure/buzz/bin/purge-desktop-agents.sh --dry-run   # list what would go
infrastructure/buzz/bin/purge-desktop-agents.sh             # do it
```

**It is the second step, not the first.** Purging while a `Welcome` channel still exists buys
minutes: the channel is the trigger.

## Order — the trigger first, then the agents

Per community, in Buzz Desktop:

1. **Delete the `Welcome` channel** (the private `stream` one, exactly that name). This is what calls
   `ensureWelcomeTeam`. Nothing else needs deleting to stop provisioning — `general` and
   `welcome-everyone` are cosmetic and trigger nothing.
2. **Then** Agents (left sidebar) → **Stop running agents** → each card's **⋮** → **Delete agent**.
   Delete every agent bound to that community's relay URL.
3. Repeat for the other community. Agents are listed machine-wide, so check `relay_url` rather than
   assuming the list is per community.

The client records `buzz-welcome-channel-ensured.v2` in local storage, so a deleted welcome channel
is not recreated.

## Personas: cannot be deleted, but can be deactivated

Built-in personas are undeletable by an explicit guard, and this is not the team blocking you:

```rust
if persona.is_builtin { return Err("Built-in agents cannot be deleted.".to_string()); }
```

The `referenced_by_team` rule below it applies to custom personas. So there is no delete path, ever.

**But they can be deactivated** — removed from "My Agents" — which stops them rendering.
`validate_persona_activation_change` refuses only when a managed agent or a team references the
persona. So the order is:

1. Remove every managed agent first (above). With none left, the ⋮ → Delete on a persona card
   deactivates it. This worked immediately for Fizz and Honey.
2. Pollen stays blocked, because the built-in `Welcome Team` still references `builtin:bumble` and
   the team cannot be emptied through the UI.
3. With **Buzz quit**, clear the team's `persona_ids` in `agents/teams.json` and set
   `is_active: false` on the persona in `agents/managed-agents.json`.

Verified 2026-09-13: this **survives a relaunch**. The built-in team is not re-seeded over an
edited file, so all three stay hidden and the Agents screen is empty.

Distinguishing the two in `~/Library/Application Support/xyz.block.buzz.app/agents/managed-agents.json`:

| | `is_builtin` | `pubkey` | runs |
|---|---|---|---|
| persona (template) | `true` | empty | no |
| managed agent | `false` | set | yes |

## Verify

```sh
pgrep -fl buzz-acp                  # expect nothing
python3 - <<'PY'
import json, pathlib
p = pathlib.Path.home()/"Library/Application Support/xyz.block.buzz.app/agents/managed-agents.json"
for a in json.load(p.open()):
    if a["pubkey"]:
        print("STILL PRESENT:", a["name"], a["pubkey"][:12], a.get("relay_url"))
PY
```

And on the relay, that no agent key is a member:

```sh
ssh nano 'cd /mnt/ssd/buzz/deploy && ./buzzctl admin list-members'
```

## The general lesson

An opinionated client provisions **server-side** resources into a community on join, and holds a
**machine-wide** agent roster with no community scope. The crew's community shape must be asserted
deliberately — WP-9 owns the channel layout, and the community itself should be created through the
operator control plane with an explicit host and owner rather than furnished by whatever client
opens it first.


---

# Executed 2026-09-13

Final state: **no agent processes on the Mac, no agents with identities in the config**, three inert
personas left, and one active community (`nostromo.backspring.xyz`) with two channels and one
member — the owner. 17 probes pass.

## What actually blocked it, which was none of the things first suspected

**Deleting an agent leaves its `channel_members` row behind.** That orphan row is what stops the
channel being deleted, and every provision-and-delete cycle added another. The `Welcome` channel in
the deleted `buzz.` community had accumulated **nine** agent rows for six agents; `nostromo.`'s had
five for three. This looks like an upstream bug: deleting an agent should take its channel
memberships with it. It matters for WP-9, when seven crew identities start joining and leaving
channels.

Repair: delete the orphan rows, then `buzz-admin reconcile-channels --channel <uuid>` to republish
the roster. Note reconcile **refuses on a deleted channel** — which is correct, not a failure.

## Two wrong diagnoses along the way, with the same cause

1. "The channel deletion did not work" — it had. `channels.deleted_at` was set; the row remains
   because it is a **soft delete**. Checked for the row's existence and used `updated_at ==
   created_at` as evidence instead of reading the `deleted_at` column in the schema printed moments
   earlier.
2. "Two new agents were spawned by opening the channel" — they were pre-existing orphan rows, not
   new agents. Same cause: reading `channel_members` without joining against what still exists.

Both were avoidable by checking the soft-delete column that the schema dump had already shown.

## The shortcut that worked

Deleting the whole `buzz.backspring.xyz` community removed its three channels, twelve memberships
and nine stray agent identities in one approved operation — 607 rows — instead of nine manual
removals. When a community exists only as a test, deleting the community beats tidying it.
