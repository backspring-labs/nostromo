# WP-3 evidence — owner identity and relay control

**Date.** 2026-09-13. Covers NOSTROMO-PLAN-0001 §10.1–§10.4.

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

**The placeholder was worse than the deviation recorded.** DEV-002 described an unused config
value; `list-members` showed `d9775d28...` registered as an **admin**. Unusable — its private half
was generated and discarded — but a phantom admin is not an unused setting. Removed; the owner is
now the sole member.

### The wipe that was not needed

The plan was to wipe the data volumes so the community would be created clean with the right owner.
Claude Code's classifier refused the volume removal as destructive, which prompted the check that
should have come first: the `communities` table **has no owner column**. Ownership is read from
`RELAY_OWNER_PUBKEY` at runtime. Restarting with the real key was sufficient. Data, certificate and
community all survived a step that would have destroyed them for no reason.

A stale community row for `nano.tailc69e7d.ts.net` remains from before the hostname switch. Inert —
communities bind by request Host — and `buzz-admin deletions` removes it when wanted.

---

## Three agents were created on the Mac, and are gone

Onboarding provisioned and started three managed agents — Fizz, Honey and Pollen — with real Nostr
identities and running `buzz-acp` processes. **No crew agent is supposed to run on the Mac**
(NOSTROMO-0002 §35.4); it is the cockpit. They were deleted the same evening. No processes remain,
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
