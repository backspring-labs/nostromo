# WP-3 evidence — owner identity and relay control

**Date.** 2026-09-13. Covers Bootstrap Plan §10.1–§10.4.

---

## §10.1 Buzz Desktop

`desktop-v0.5.23`, `Buzz_0.5.23_aarch64.dmg`, sha256
`9197dde29a09ade77f56677e07cb4d6a9d7d1a6a157d7212f0a050144059c5b2`, at `/Applications/Buzz.app`.

The **disk image carries no signature** — `spctl` rejects it, which looks alarming and is not. The
**app inside is signed and notarized by Block, Inc., Team ID `EYF346PHUG`**, and Gatekeeper accepts
it. Verified on the installed copy rather than on the mounted image, so the check covers what runs.

## §10.2 Owner identity

```text
npub  npub12zxdr37mehwvjwupdzfretzfau5tkqhsucx72j0yfvqsqrftee0sp8a962
hex   508cd1c7dbcddcc93b8168923cac49ef28bb02f0e60de549e44b01000d2bce5f
```

Minted in Buzz Desktop. The private key is in the macOS Keychain (service `buzz-desktop`, account
`secrets`); Buzz derives the public key at runtime, so no file holds it. Backed up by the owner to
a password manager and to a NIP-49 `ncryptsec` file — scrypt at 2^18, roughly 256 MiB per guess,
and a standard format, so recovery does not depend on Buzz Desktop still existing.

`infrastructure/buzz/bin/nostr_keys.py` does the hex/npub conversion. It self-tests against the
BIP-340 and NIP-19 vectors and refuses to run if they fail, because a subtly wrong derivation here
would make the owner unable to authenticate to their own relay.

## §10.3 Owner authentication — and DEV-002 closed

`RELAY_OWNER_PUBKEY` moved from the DEV-002 placeholder to the real key. The relay promoted the
owner on restart, and the owner authenticated from Buzz Desktop:

```text
NIP-42 auth successful   pubkey 508cd1c7...
HTTP bridge request      route /query   status 200
```

The placeholder appeared in `list-members` as an **admin**, not merely as a config value. That is
exactly what DEV-002's own swap procedure anticipated — *"the relay demotes the placeholder to
admin, then it is removed"* — and an earlier reading of this evidence wrongly called it a gap in
the deviation. It was documented; it was simply demoted rather than deleted, which is the designed
behaviour. `buzz-admin remove-member` removed it, and the owner is now the sole member.

### The wipe that was not needed

The plan was to wipe the data volumes so the community would be created clean with the right owner.
Claude Code's classifier refused the volume removal as destructive, which prompted the check that
should have come first: the `communities` table **has no owner column**. Ownership is read from
`RELAY_OWNER_PUBKEY` at runtime. Restarting with the real key was sufficient. Data, certificate and
community all survived a step that would have destroyed them for no reason.

### The stale community, removed

The `nano.tailc69e7d.ts.net` community from before the hostname switch was deleted the same evening
through `buzz-admin deletions`, which is a four-stage control plane worth describing: `submit`
freezes a cross-store inventory and hashes it, `inspect` shows what the hash covers, `approve`
signs off **that specific digest**, and only `run` deletes. The contents cannot change between
approval and execution.

Approved inventory: **3 rows** — 1 `audit_log`, 1 `events`, 1 `relay_members` (the discarded DEV-002
placeholder). No channels, users or media. Result: `deletion_state = tombstone`, zero members,
events and channels. The live community was untouched (1 member, 166 events, 3 channels) and all 17
probes pass.

**Trap.** `deletions submit --host` **defaults to `RELAY_URL`'s authority**, which is now the live
community. Omitting `--host` would have queued `buzz.backspring.xyz` for deletion. The approval gate
would have caught it — the inventory would have read 166 events rather than 3 — but only for an
operator who actually reads the inventory before approving. Always pass `--host` explicitly.

This also confirmed that communities are genuinely isolated tenants: `community_id` is the leading
column of the primary key on `relay_members`, `channels` and `events`, and the two communities
carried different owners. `RELAY_OWNER_PUBKEY` seeds the owner at community creation rather than
overriding relay-wide, which is why the old community still showed the placeholder as its owner
after the new one had been corrected.

---

## Three agents were created on the Mac, and are gone

Onboarding provisioned and started three managed agents — Fizz, Honey and Pollen — with real Nostr
identities and running `buzz-acp` processes. **No crew agent is supposed to run on the Mac**
(Operating Model §35.4); it is the cockpit. They were deleted the same evening. No processes remain,
and only the owner is a relay member. Three built-in *persona templates* remain and cannot be
deleted while a built-in team references them: they hold no keys and run nothing.

### What they did before removal

| Agent | Kinds | |
|---|---|---|
| Fizz `b991738c` | 0, 9 | profile, and one chat message |
| Honey `42c1ecf7` | 0 | profile |
| Pollen `ed9ee017` | 0 | profile |

Four events between 01:21:15 and 01:22:31, still in the database, from identities that no longer
exist.

**This was not an enforcement failure, and the first analysis saying so was wrong.**
`BUZZ_REQUIRE_RELAY_MEMBERSHIP=true` does not gate writes: Buzz's security model states that
**channel membership is the only access control mechanism**, and onboarding placed these agents in
the welcome channel. The relay behaved as designed. Relay membership and channel membership are
different gates, and the crew's design must not assume the first implies the second.

**Two analysis errors worth keeping**, because both are the same shape as the day's others:

1. "They authenticated despite not being members" — NIP-42 is authentication, not authorization. A
   successful auth from a non-member is expected.
2. "They wrote nothing" — the events query was piped through `head -12` against a count-descending
   list, so the single-event rows fell below the cut. A conclusion drawn from a truncated view.

## What remains open

- Three built-in personas and the built-in "Welcome Team" cannot be deleted. Harmless; revisit in WP-9.
- Four events from deleted identities persist in the relay database.
- Channels `general`, `Welcome`, `welcome-everyone` were created by onboarding. Left deliberately;
  the crew's channel layout is WP-9's decision, not a tidy-up.
- §10.5 Herdr remote connectivity was proven in WP-4 evidence part 2.

---

# Multi-tenancy, validated before minting identities

The owner declined to accept a single-hostname config ahead of WP-5, on the grounds that the relay's
ability to carry more than one community should be proven before seven handles are bound to a host.
That was the right call and it found four things.

## What is genuinely per-community

`community_id` leads the primary key on `relay_members`, `channels` and `events`. Two communities
ran side by side with separate certificates, separate event counts and the same owner:

```text
nostromo.backspring.xyz   CN=nostromo.backspring.xyz   1 member (owner)     1 event
buzz.backspring.xyz       CN=buzz.backspring.xyz       1 member (owner)   169 events
```

## Media: the limitation does not exist, after three wrong readings

This section previously claimed every community's media links carry the primary community's
hostname. **That is false.** The relay rewrites media URLs per tenant:

```rust
fn media_base_url_for_tenant(..) -> String { format!("{scheme}://{tenant_host}/media") }
descriptor.url = format!("{base}/{}.{ext}", descriptor.sha256);
```

`rewrite_descriptor_urls_for_tenant` rebuilds every blob descriptor from the **request's** host;
`BUZZ_MEDIA_BASE_URL` contributes only the scheme. A blob uploaded in `buzz.backspring.xyz` is
served from `buzz.backspring.xyz`. There is no branding leak and no cross-community breakage.

The design is careful: raw bytes are shared content-addressed storage, while the per-tenant read
gate is a sidecar at `_meta/{community}/{sha}.json`, checked before any blob I/O because *"Storage
is not authoritative"* — so a blob in another community is never observable through a global lookup.

`BUZZ_MEDIA_BASE_URL` must still name a **mapped community host**, because media reads bind a tenant
from the request host and an unmapped host 404s. A neutral `media.backspring.xyz` was configured,
certificated, measured and reverted for that reason:

```text
nostromo.backspring.xyz   /media/<hash> -> 401 {"error":"authentication failed"}
media.backspring.xyz      /media/<hash> -> 404 {"error":"not found"}
```

### Three wrong readings, and what they have in common

1. "Media base URL is global, so links leak the primary host" — read the parse, not the rewrite.
2. "Media routes are not tenant-bound, so a neutral host works" — caught by measuring, not reading.
3. "Links in one community will point at another and 404" — read the descriptor build, not the
   rewrite that follows it.

Each was a confident conclusion from reading one layer of a path that had another layer below it.
The one that got caught early was the one that was **measured** rather than reasoned about. The
owner's repeated "that doesn't seem right" was correct every time, against three confident answers.

## Communities do not auto-create — corrected

An earlier note in `buzz.env` claimed a hostname creates a community on first connection. It does
not. `bind_community` **fails closed**: *"an unmapped host or a lookup failure fails closed with a
generic rejection — never a default tenant"*, returning 404 without echoing the host so a caller
cannot probe which communities exist.

Only `RELAY_URL`'s host is auto-provisioned at startup, which is how all three of this deployment's
communities came to exist — each was `RELAY_URL` at some point today. **`buzz.backspring.xyz` works
side by side with `nostromo.backspring.xyz` by accident of history, not by configuration.**

The supported path is the operator control plane: `POST /operator/communities` with `host` and
`initial_owner_pubkey`, NIP-98 signed by a key in `RELAY_OPERATOR_PUBKEYS` against
`RELAY_OPERATOR_API_ORIGIN`, with per-deployment tenant limits. Neither variable is set here. The
same surface offers `archive`, `unarchive`, `transfer` and `list_owned_communities`.

## An upstream observation

The tombstoned `nano.tailc69e7d.ts.net` community logs `NIP-43 membership reconciliation failed —
community write fenced` every 60 seconds. The deletion request is at `retention_pending`, unblocked
and with no error, so the deletion is proceeding as designed; the background reconciler simply does
not skip tombstoned communities. Log noise, not damage, and it should stop when retention elapses.

---

# The client provisions; the relay does not

Joining `nostromo.backspring.xyz` produced the same three channels the `buzz.` community has —
`Welcome`, `general`, `welcome-everyone` — which looked like an isolation failure and is not:

```text
Welcome           buzz     d944d4a0   01:21:09
Welcome           nostromo cb959b66   02:32:32
general           buzz     25b415b2   01:21:09
general           nostromo 34f6c608   02:32:31
```

Distinct ids, distinct communities, created seventy minutes apart, 174 events against 54. **Buzz
Desktop created them**, under the owner's key, as its default set for a new community. The relay
provisioned nothing.

The managed-agent roster behaves differently again: `managed-agents.json` lives in the app's
support directory and is **per installation, not per community**, so the agent list — and the two
agents deleted earlier — follows the owner into every community opened on that machine. Nothing was
deleted "in nostromo"; there is only one list.

## Why this matters beyond tidiness

An opinionated client is creating **server-side resources** in a community without being asked, and
holds a machine-wide notion of "your agents" that has no community scope at all. For a small team's
chat app that is friendly. For a relay run as infrastructure it means **the crew's community shape
must be asserted deliberately, not inherited from whatever a client does on join.**

Two consequences for later work:

- **WP-9** defines the crew's channel layout. That is the point to replace the defaults, not before;
  deleting them now means deleting them twice.
- The crew's community should be created through the **operator control plane** —
  `POST /operator/communities` with an explicit host and initial owner — rather than appearing as a
  side effect of `RELAY_URL` at startup and then being furnished by a client. That surface is now
  enabled; it was disabled (empty `RELAY_OPERATOR_PUBKEYS`, fail closed) until 2026-09-13.

Open question worth one cheap observation: whether Desktop provisions defaults on community
**creation** or on every **open**. Deleting the three channels once and reopening answers it.
