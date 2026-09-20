#!/usr/bin/env bash
# Run a `buzz` command as the owner, with the key taken from the macOS Keychain.
#
#   with-owner-key.sh messages get --channel <uuid> --limit 20
#   with-owner-key.sh channels list
#
# Runs on the Mac only, and only where Buzz Desktop is installed. The key is read into a variable
# for the life of one command and never written anywhere, never printed, and never passed as an
# argument — `buzz` takes it from the environment, so it does not appear in `ps`.
#
# Why this exists: the crew's channel is private, so reading it needs a member's key. Every crew
# key lives in that role's 700 home on the Spark and must stay there; the owner's key is on the Mac
# where Buzz Desktop already keeps it. Without this, checking what a role actually said means
# turning on ACP tracing and reading it as root, which is a poor way to answer "what did she say".
set -euo pipefail
[[ $# -gt 0 ]] || { echo "usage: with-owner-key.sh <buzz args...>" >&2; exit 1; }

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"

# Selection is by derived PUBLIC key against the manifest, because the Keychain item holds every
# identity Buzz Desktop manages and the first one in it is a Desktop-managed agent, not the owner.
# No candidate is ever printed.
KEY="$(python3 - "$REPO" <<'PY'
import json, re, subprocess, sys, pathlib
sys.path.insert(0, str(pathlib.Path(sys.argv[1]) / "infrastructure" / "buzz" / "bin"))
import nostr_keys as nk

manifest = (pathlib.Path(sys.argv[1]) / "crew" / "manifest.yaml").read_text()
m = re.search(r"^owner:\n(?:.*\n)*?\s+buzz_pubkey:\s*([0-9a-f]{64})", manifest, re.M)
if not m:
    sys.exit("no owner.buzz_pubkey in crew/manifest.yaml")
want = m.group(1)

try:
    blob = subprocess.run(
        ["security", "find-generic-password", "-s", "buzz-desktop", "-a", "secrets", "-w"],
        capture_output=True, text=True, check=True).stdout
except FileNotFoundError:
    sys.exit("`security` not found — this script is macOS only")
except subprocess.CalledProcessError:
    sys.exit("Keychain read failed or was denied. Unlock the login keychain and allow access.")

cands = re.findall(r"nsec1[02-9ac-hj-np-z]{50,}", blob)
cands += re.findall(r"(?<![0-9a-f])[0-9a-f]{64}(?![0-9a-f])", blob)
del blob
for c in dict.fromkeys(cands):
    h = c
    if h.startswith("nsec1"):
        try:
            _, h = nk.bech32_decode(h)
        except Exception:
            continue
    if not re.fullmatch(r"[0-9a-f]{64}", h):
        continue
    try:
        if nk.xonly_pubkey(h) == want:
            print(h)
            break
    except Exception:
        continue
else:
    sys.exit("no key in the Keychain derives the manifest owner pubkey")
PY
)"

RELAY="$(awk '/^relay:/{f=1} f && /url:/{print $2; exit}' "$REPO/crew/manifest.yaml")"
BUZZ_PRIVATE_KEY="$KEY" BUZZ_RELAY_URL="$RELAY" exec buzz "$@"
