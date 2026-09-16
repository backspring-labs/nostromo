#!/usr/bin/env python3
"""Publish this role's Buzz profile (kind:0), setting its NIP-05 handle.

RUNS ON THE ROLE'S OWN ACCOUNT. That is the point: signing centrally would mean reading all seven
private keys, which would undo the per-account isolation those keys live inside. Each role signs
its own metadata with a key no other role can read.

Posts to the relay's HTTP bridge with NIP-98 auth rather than opening a WebSocket, because the
standard library has no WebSocket client and the bridge is a supported door.

Usage: publish-profile.py [--dry-run]
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import pathlib
import sys
import time
import urllib.error
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import nostr_keys as nk  # noqa: E402

MANIFEST = os.environ.get("NOSTROMO_MANIFEST", "/opt/nostromo/nostromo-src/crew/manifest.yaml")
KEY = pathlib.Path.home() / ".config/nostromo/secrets/buzz.key"
DRY = "--dry-run" in sys.argv


def main() -> int:
    if nk.selftest_quiet() != 0:
        sys.exit("key tool self-test failed; refusing to sign anything")

    role = os.environ.get("NOSTROMO_ROLE") or pathlib.Path.home().name
    import yaml
    agents = yaml.safe_load(open(MANIFEST))["agents"]
    if role not in agents:
        sys.exit(f"{role} is not in the manifest")
    agent = agents[role]

    sk = KEY.read_text().strip()
    pub = nk.xonly_pubkey(sk)
    if pub != agent["buzz_pubkey"]:
        sys.exit(f"key on disk derives {pub[:16]}… but the manifest says {agent['buzz_pubkey'][:16]}…")

    handle = agent["nip05"]
    host = handle.split("@", 1)[1]
    url = f"https://{host}/events"

    # kind:0 — the profile. `name` is what NIP-05 resolves on; the relay lowercases the lookup.
    profile = nk.sign_event(sk, 0, json.dumps({
        "name": role,
        "display_name": agent.get("display_name", role.capitalize()),
        "nip05": handle,
        "about": agent.get("capability", ""),
    }, separators=(",", ":")))
    body = json.dumps(profile, separators=(",", ":")).encode()

    # kind:27235 — NIP-98 auth. The payload tag binds the signature to this exact body, so the
    # header cannot be lifted onto a different request.
    auth = nk.sign_event(sk, 27235, "", tags=[
        ["u", url],
        ["method", "POST"],
        ["payload", hashlib.sha256(body).hexdigest()],
    ], created_at=int(time.time()))
    header = "Nostr " + base64.b64encode(
        json.dumps(auth, separators=(",", ":")).encode()).decode()

    print(f"  role     {role}")
    print(f"  pubkey   {pub}")
    print(f"  nip05    {handle}")
    if DRY:
        print("  dry run — nothing sent")
        return 0

    req = urllib.request.Request(url, data=body, method="POST", headers={
        "Content-Type": "application/json", "Authorization": header, "Host": host})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print(f"  published  HTTP {r.status}  {r.read(200).decode()[:120]}")
    except urllib.error.HTTPError as e:
        print(f"  FAILED     HTTP {e.code}  {e.read(300).decode()[:200]}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
