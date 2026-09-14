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

## Personas and the team: leave them

The three `builtin:*` **personas** hold no keys, run nothing, and cannot be deleted while the
built-in `Welcome Team` references them — `validate_persona_activation_change` refuses when a
persona is `referenced_by_team`, and the built-in team itself cannot be deleted. That is a dead end
and not worth pursuing: an inert template is not an agent.

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
