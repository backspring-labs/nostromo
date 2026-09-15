# WP-5 evidence — seven crew Buzz identities

**Date.** 2026-09-14. Covers NOSTROMO-PLAN-0001 §12.1–§12.5 and §12.8.
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

## Still open in WP-5

- §12.6 allowlist generation — **crew-wide for v1**, an owner decision. The allowlist governs who
  may *address* an agent, not what an agent may *do*; the doing is constrained by the permission
  profiles, path boundaries, rulesets and App permissions. Deriving edges now would encode an
  assumption about a lifecycle nobody has run. The commissioning roll should record who actually
  addressed whom so the edges come from measurement rather than guesswork.
- §12.7 enrolment in `#nostromo-control` — the control channel does not exist yet.
- Encrypted backup of all seven private keys to the Spark and the Mac, owner passphrase.
