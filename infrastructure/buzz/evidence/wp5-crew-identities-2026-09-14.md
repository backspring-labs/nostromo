# WP-5 evidence — seven crew Buzz identities

**Date.** 2026-09-14. Covers Bootstrap Plan §12.1–§12.5 and §12.8.
Community `nostromo.backspring.xyz`, owner `508cd1c7…ce5f`.

## The identities

| Role | NIP-05 | Public key | Private key |
|---|---|---|---|
| mother | `mother@nostromo.backspring.xyz` | `0fe13d87cb0051685da767d8de393a2d8fff155fbcf1feeb0b1ca4f877a5b063` | `spark:~mother/.config/nostromo/secrets/buzz.key` |
| ash | `ash@nostromo.backspring.xyz` | `e5a173a7e5ce83c5c228398711659f49262b1b768cea33832e78435709317697` | `spark:~ash/…` |
| ripley | `ripley@nostromo.backspring.xyz` | `5dd000d70cfb4316de6a81b7ea30a0eef59302522a9544add0cfc9cacae9ec44` | `spark:~ripley/…` |
| dallas | `dallas@nostromo.backspring.xyz` | `bfdf455488c1bddbb9a61f287c32ec7d940da566e96f6d262f60409b5b6c55a2` | `spark:~dallas/…` |
| parker | `parker@nostromo.backspring.xyz` | `1a4e1fbefce7f6e0b63123fd86e4dce63a538614eecf443712377b5e557fee47` | `spark:~parker/…` |
| brett | `brett@nostromo.backspring.xyz` | `3b7b029c96843910fc4660d7d22c514d69804f174fff43c74eaaa389b3fef14d` | `spark:~brett/…` |
| lambert | `lambert@nostromo.backspring.xyz` | `d17abac99a72f16b48e4548eb1f9220f6de040125e4c1cf05672fafc766085b7` | `spark:~lambert/…` |

Every private key is mode 600 in its own role's 700 directory, owned by that role's Unix account.

## Generated in place, not centrally — twice for the same reason

The plan says generate with `buzz-admin generate-key`, which runs in the relay container: every key
would have travelled nano → Spark. **Generated on the account that uses it instead**, so no key has
ever existed on a host that does not need it.

The same argument decided how profiles were published. Setting a NIP-05 handle means publishing a
signed kind:0 event, and there is no signing CLI in the pinned image. Signing all seven centrally
would have meant **reading all seven private keys**, undoing the per-account isolation those keys
live inside. Each role signs its own metadata, on its own account, with a key no other role can
read.

### What that cost, and how it is made checkable

It required implementing BIP-340 Schnorr by hand — the only cryptography in this repository. It is
verified against the **three official BIP-340 test vectors**, a sign/verify round trip, and a
**tampered-signature rejection**, and `publish-profile.py` refuses to sign anything if those fail.
A verifier that only ever says yes proves nothing.

Derivation was cross-checked against `buzz-admin generate-key` on a throwaway key before any real
key was generated. **The first cross-check failed** — `nostr_keys.py` had no derive-from-secret path
and was treating the secret as a public key, so it encoded and decoded the secret and reported a
mismatch that was entirely the test's fault. `--pub` is now explicit, because a bare 64-character
hex is ambiguous between the two and guessing produces a plausible-looking answer.

## §12.8 Identity-only test — all pass

```text
count 7                       PASS      all distinct                  PASS
all 64 hex chars              PASS      none is the owner's key       PASS
none is the relay's key       PASS      parker cannot read ripley's   PASS
                                        dallas cannot read parker's   PASS

relay membership
  all seven registered        PASS      no unexpected members         PASS
  owner present and distinct  PASS      crew are members not owners   PASS
  control: a freshly generated stranger is not a member               PASS

NIP-05 resolution through the relay's .well-known endpoint
  seven handles -> seven manifest keys, each advertising wss://nostromo.backspring.xyz   PASS
  control: an unregistered name returns an empty names object                            PASS
```

The controls are the half that establishes anything. A membership list that only ever admits and a
lookup that only ever resolves have not been shown to exclude anything.

## §12.6 Allowlist — crew-wide for v1

`crew/allowlist.yaml`, generated from the manifest. Every crew member accepts the owner and the six
other roles, and nobody else. It governs who may *address* an agent, not what an agent may *do* —
the doing is held by the OpenCode permission profiles, path boundaries in CI, branch rulesets, App
permissions and one Unix account per role. Parker cannot make Dallas approve something by messaging
Dallas: Dallas's App has no contents write and the ruleset requires a review from a non-author.

Narrower edges would encode an assumption about a lifecycle nobody has run, and a wrong edge fails
as an agent silently unable to do its job — harder to diagnose than a message that should not have
been allowed. **The commissioning roll should record who actually addresses whom**, so the edges are
derived from measurement rather than guesswork.

The residual, stated in the file: a role can message the role reviewing its work. That is influence,
not a permissions hole, and the answer is Dallas's instructions — messages from the authoring role
are context, never evidence.

## §12.7 The standing channel

**`#nostromo`** — private, stream, created 2026-09-14. Eight members: the owner and all seven crew,
each matching its manifest handle.

It is named for the ship because it is the only channel that is about the ship. Every other channel
will be about a piece of work and will end with it. Platform Spec §17 called for a control channel
and then listed it among the work-item channels, muddling its own distinction; that is amended in
the spec rather than quietly fixed.

Why it had to come first: the design rests on each role holding real authority inside its remit and
stopping sharply at its edge, and stopping is only safe if there is somewhere to stop *to*. Without
this channel a role at the limit of its authority has nowhere to hand the decision back, and the
only available failure is to proceed anyway — the exact class of failure the crew exists to prevent.

## Key backup

`crew-buzz-keys-20260915T020700Z.tar.gz.enc` — all seven private keys plus the manifest, AES-256
with PBKDF2 at 600k iterations, passphrase held only by the owner. Two copies, byte-identical by
sha256: `~/.nostromo/backups/crew-keys/` on the Mac and `/opt/nostromo/backups/crew-keys/` on the
Spark, both mode 600. No crew role can read the Spark copy.

Collected by ssh'ing **as each role**, so no single account ever held all seven on disk. The bundle
was decrypted and its seven keys counted **before** distribution — an unverified backup is a guess.

Agent keys are replaceable in a way the owner's key is not: if all seven were lost they could be
regenerated and re-registered in minutes. What cannot be recovered is provenance — past messages and
commits stay under the old keys. So this protects confidentiality first and recovery second.

## WP-5 is complete


---

# Retiring an identity is a supported flow, not a cleanup job

Established 2026-09-14 while chasing what looked like leftover rows from Buzz Desktop's deleted
default agents. It was not residue. **Every published agent tombstones on deletion**, enqueueing a
**NIP-IA kind:9035 archive request** in the same transaction as the local removal — which, per the
source, *"stops the identity appearing in member pickers and autocomplete"*.

All seven deleted identities were present in `archived_identities` with `consent_path: admin`, the
owner as `actor`, `reason: retired`, and a `request_event_id` pointing at the archive request.
Seven kind:9035 events and seven kind:5 deletions existed alongside them.

The user rows and kind:0 profiles persisting is **correct**: Nostr is an append-only log of signed
events, and a published identity is retracted by archival rather than deletion. An earlier reading
of this called it an upstream defect and removed those rows by hand — unnecessary, and it deleted
records the system deliberately retains.

**For WP-9.** Retiring a crew role uses this flow: archive the identity (kind:9035), leave its
channels, remove relay membership. Its published events and authored commits remain, which is right
— that history is the provenance the evaluation depends on. Do not hand-delete rows.
