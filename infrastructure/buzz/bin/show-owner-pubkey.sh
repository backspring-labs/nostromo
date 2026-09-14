#!/usr/bin/env bash
# Print the owner's PUBLIC key from the Buzz Desktop identity in the macOS Keychain.
#
# Buzz derives the public key at runtime from the keyring-held private key, so there is no file to
# read it from and the app does not always surface it. This reads the Keychain entry, derives the
# public half locally, and prints ONLY public material — never the private key, in any branch.
#
# macOS will prompt for Keychain access. Run it yourself; nothing here transmits anything.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$HERE/nostr_keys.py" --selftest >/dev/null || { echo "key tool self-test failed; refusing" >&2; exit 1; }

secret="$(security find-generic-password -w -s buzz-desktop -a secrets 2>/dev/null)" \
  || { echo "no Buzz identity found in the Keychain (service buzz-desktop, account secrets)" >&2; exit 1; }

printf '%s' "$secret" | python3 -c '
import json, subprocess, sys, os
raw = sys.stdin.read().strip()
here = os.path.dirname(os.path.abspath(sys.argv[1]))

def pub_from_sec(sec):
    return subprocess.run([sys.executable, os.path.join(here, "nostr_keys.py"), sec],
                          capture_output=True, text=True, check=True).stdout.strip()

sec = None
try:
    d = json.loads(raw)
    # Prefer an explicit public key if the blob carries one; never touch other fields.
    for k, v in d.items():
        if "pub" in k.lower() and isinstance(v, str) and len(v) in (63, 64):
            print("found stored public key")
            hexpub = v if len(v) == 64 else pub_from_sec(v)
            break
    else:
        hexpub = None
        for k, v in d.items():
            if isinstance(v, str) and (len(v) == 64 or v.startswith("nsec1")):
                sec = v
                break
        if sec is None:
            sys.exit("could not find a key in the stored identity")
        hexpub = pub_from_sec(sec)
except json.JSONDecodeError:
    hexpub = pub_from_sec(raw)

npub = subprocess.run([sys.executable, os.path.join(here, "nostr_keys.py"), hexpub],
                      capture_output=True, text=True, check=True).stdout.strip()
print()
print("  hex :", hexpub)
print("  npub:", npub)
print()
print("Both of the above are PUBLIC. Safe to paste anywhere.")
' "$HERE/show-owner-pubkey.sh"
