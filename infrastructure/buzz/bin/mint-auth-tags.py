#!/usr/bin/env python3
"""Mint NIP-OA owner attestations for the Nostromo crew.

An agent proves who owns it with a signed `auth` tag:

    preimage = "nostr:agent-auth:<agent_pubkey_hex>:<conditions>"
    sig      = BIP-340 Schnorr( SHA256(preimage), owner_seckey )
    tag      = ["auth", "<owner_pubkey_hex>", "<conditions>", "<sig_hex>"]

buzz-acp reads it from BUZZ_AUTH_TAG and verifies it against the agent's own pubkey. Without one:
`buzz mem set` fails with "owner pubkey required", so no agent can write core memory, and buzz-acp
injects an onboarding nudge every turn telling it to do the thing it cannot do. Attestations also
let agents recognise each other as siblings of the same owner.

The tag is NOT a secret. It proves owner→agent binding; holding it does not let anyone act as the
agent, which still needs the agent's own key. So the tags are committed to crew/manifest.yaml
alongside the pubkeys they authorise.

The OWNER'S KEY IS. It is read from a no-echo prompt, used to sign, and never stored, printed,
logged, or written anywhere. Run this on the machine that holds it.

Usage:  mint-auth-tags.py [--keychain] [--conditions <str>] [--dry-run]

  --keychain  read the owner key from the macOS Keychain (service "buzz-desktop", account
              "secrets"), where Buzz Desktop stores it. Avoids the key passing through a
              terminal, a clipboard or scrollback. macOS will prompt once for access.
"""
import getpass
import hashlib
import subprocess
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import nostr_keys as nk  # noqa: E402

REPO = Path(__file__).resolve().parents[3]
MANIFEST = REPO / "crew" / "manifest.yaml"


def die(msg: str) -> None:
    print(f"mint-auth-tags: {msg}", file=sys.stderr)
    sys.exit(1)


def read_manifest_agents(text: str) -> list[tuple[str, str]]:
    """[(role, pubkey_hex)] in file order, from the agents: block."""
    out, role, in_agents = [], None, False
    for line in text.splitlines():
        if re.match(r"^agents:\s*$", line):
            in_agents = True
            continue
        if in_agents and re.match(r"^[a-z_]+:", line):
            break                                   # next top-level key
        if not in_agents:
            continue
        m = re.match(r"^  ([a-z]+):\s*$", line)
        if m:
            role = m.group(1)
        m = re.match(r"^    buzz_pubkey:\s*([0-9a-f]{64})\s*$", line)
        if m and role:
            out.append((role, m.group(1)))
    return out


def owner_pubkey_from_manifest(text: str) -> str:
    m = re.search(r"^owner:$.*?^  buzz_pubkey:\s*([0-9a-f]{64})\s*$",
                  text, re.M | re.S)
    return m.group(1) if m else ""


def auth_tag(owner_sk_hex: str, owner_pk_hex: str, agent_pk_hex: str, conditions: str) -> str:
    if owner_pk_hex == agent_pk_hex:
        die("owner and agent pubkeys are identical — self-attestation is rejected")
    preimage = f"nostr:agent-auth:{agent_pk_hex}:{conditions}"
    msg = hashlib.sha256(preimage.encode()).digest()
    sig = nk.schnorr_sign(msg, owner_sk_hex)
    if not nk.schnorr_verify(msg, owner_pk_hex, sig):
        die(f"signature failed self-verification for {agent_pk_hex[:12]} — refusing to emit it")
    return json.dumps(["auth", owner_pk_hex, conditions, sig], separators=(",", ":"))


def main() -> int:
    args = sys.argv[1:]
    dry = "--dry-run" in args
    conditions = ""
    if "--conditions" in args:
        conditions = args[args.index("--conditions") + 1]
    # Mirrors buzz-sdk validate_conditions: empty is allowed; otherwise no whitespace and
    # non-empty '&'-separated clauses. A malformed value fails verification at startup, silently
    # falling back to --agent-owner, so reject it here where the error is visible.
    if conditions:
        if any(c.isspace() for c in conditions):
            die("conditions must not contain whitespace")
        if any(part == "" for part in conditions.split("&")):
            die("empty clause in conditions (leading, trailing or doubled '&')")

    if nk.selftest_quiet() != 0:
        die("nostr_keys self-test failed — refusing to sign anything")

    text = MANIFEST.read_text()
    agents = read_manifest_agents(text)
    if not agents:
        die(f"no agents with a buzz_pubkey found in {MANIFEST}")
    expected_owner = owner_pubkey_from_manifest(text)

    print(f"Minting {len(agents)} attestations from {MANIFEST.relative_to(REPO)}")
    print(f"  conditions: {conditions!r}" + ("  (unscoped)" if not conditions else ""))
    print("\nThe owner key is used to sign and is never stored or displayed.")
    if "--keychain" in args:
        try:
            blob = subprocess.run(
                ["security", "find-generic-password", "-s", "buzz-desktop", "-a", "secrets", "-w"],
                capture_output=True, text=True, check=True,
            ).stdout
        except FileNotFoundError:
            die("`security` not found — --keychain is macOS only")
        except subprocess.CalledProcessError:
            die("Keychain read failed or was denied. Unlock the login keychain and allow access, "
                "or omit --keychain and paste the key at the prompt.")
        # The Keychain item holds every identity Buzz Desktop manages, not just the owner's — the
        # first key in it was a Desktop-managed agent. So collect every candidate and select the
        # one that derives the manifest's owner pubkey. Selection is by PUBLIC key; no candidate
        # is ever printed, and non-matching ones are discarded.
        cands = re.findall(r"nsec1[02-9ac-hj-np-z]{50,}", blob)
        cands += re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", blob)
        del blob
        if not cands:
            die("no nsec or 64-hex key found in the Keychain item — omit --keychain and paste it")
        if not expected_owner:
            die("the manifest has no owner.buzz_pubkey, so the right key cannot be identified "
                "among the candidates — omit --keychain and paste it")
        secret = ""
        seen = set()
        for c in cands:
            if c in seen:
                continue
            seen.add(c)
            h = c
            if h.startswith("nsec1"):
                try:
                    _, h = nk.bech32_decode(h)
                except Exception:
                    continue
            if not re.fullmatch(r"[0-9a-f]{64}", h):
                continue
            try:
                if nk.xonly_pubkey(h) == expected_owner:
                    secret = h
                    break
            except Exception:
                continue
        if not secret:
            die(f"none of the {len(seen)} keys in the Keychain derive the manifest's owner "
                f"{expected_owner[:16]}… — omit --keychain and paste the owner key instead")
        print(f"Read owner key from the Keychain ({len(seen)} identities present, matched 1).")
    else:
        secret = getpass.getpass("Owner nsec or hex seckey: ").strip()
    if not secret:
        die("no key entered")
    if secret.startswith("nsec1"):
        try:
            _, secret = nk.bech32_decode(secret)
        except Exception as e:
            die(f"could not decode nsec: {e}")
    if not re.fullmatch(r"[0-9a-f]{64}", secret):
        die("key must be an nsec1... or 64 lowercase hex characters")

    owner_pk = nk.xonly_pubkey(secret)
    del_note = ""
    if expected_owner and owner_pk != expected_owner:
        die(f"this key derives {owner_pk[:16]}… but the manifest's owner is {expected_owner[:16]}…")
    if not expected_owner:
        del_note = "  (manifest has no owner.buzz_pubkey to check against)"
    print(f"\nOwner pubkey: {owner_pk}{del_note}")

    tags = {}
    for role, agent_pk in agents:
        tags[role] = auth_tag(secret, owner_pk, agent_pk, conditions)
        print(f"  {role:<8} ok  ({len(tags[role])} bytes)")
    del secret

    if dry:
        print("\n--dry-run: manifest not modified\n")
        for role, tag in tags.items():
            print(f"  {role}: {tag}")
        return 0

    # Insert or replace `buzz_auth_tag:` immediately after each role's buzz_pubkey.
    out, role = [], None
    for line in text.splitlines(keepends=True):
        m = re.match(r"^  ([a-z]+):\s*$", line)
        if m:
            role = m.group(1)
        if re.match(r"^    buzz_auth_tag:", line):
            continue                                  # drop the old one; re-emitted below
        out.append(line)
        if role in tags and re.match(r"^    buzz_pubkey:\s*[0-9a-f]{64}", line):
            out.append(f"    buzz_auth_tag: '{tags[role]}'\n")
    MANIFEST.write_text("".join(out))
    print(f"\nWrote {len(tags)} attestations into {MANIFEST.relative_to(REPO)}")
    print("They are public: review with `git diff` and commit.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
