#!/usr/bin/env bash
# Keep each crew member's Buzz profile in line with the manifest, and set avatars. From the Mac.
#
#   sync-profiles.sh [--avatars] [--dry-run] [role...]     default: every role in the manifest
#
# For each role, AS that role on the Spark — its key never leaves its own account (WP-5):
#   - display name, NIP-05 handle and about (= the manifest's capability) are set with
#     `buzz users set-profile`, which reads the current profile, merges, then signs, so the avatar
#     and anything else already there survive;
#   - with --avatars, ~/.nostromo/avatars/<role>.png is re-encoded without metadata, uploaded to the
#     relay's own media store (reachable only on the tailnet) and set as the picture. The relay
#     refuses media carrying EXIF, XMP, an ICC profile or similar with a 422, and macOS screenshots
#     carry all of them. Skipped when the profile already points at that exact file.
# Then the profile is read back and compared with the manifest, including that the key that signed
# it is the one the manifest records for that role.
#
# Nothing is published for a role that already matches. Run it after any capability rename: the
# about lines drifted once already, when Brett's `verification` became `bounded_implementation`.
#
# Replaces publish-profile.py, which built the whole profile from the manifest. A profile event
# replaces the previous one outright, so re-running that would have erased every avatar.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
MANIFEST="$ROOT/crew/manifest.yaml"
AVDIR="$HOME/.nostromo/avatars"
AVATARS=0; DRY=0; ROLES=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --avatars) AVATARS=1; shift ;;
    --dry-run) DRY=1; shift ;;
    -*)        echo "unknown flag $1" >&2; exit 2 ;;
    *)         ROLES+=("$1"); shift ;;
  esac
done
die() { echo "sync-profiles: $*" >&2; exit 1; }

agent() {  # role key -> manifest value
  python3 -c 'import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))["agents"][sys.argv[2]].get(sys.argv[3], ""))' \
    "$MANIFEST" "$1" "$2"
}
if [[ ${#ROLES[@]} -eq 0 ]]; then
  while IFS= read -r r; do ROLES+=("$r"); done < <(python3 -c 'import yaml,sys
print("\n".join(yaml.safe_load(open(sys.argv[1]))["agents"]))' "$MANIFEST")
fi

# Re-encode to IHDR/IDAT/IEND only, in sRGB. Converting from the embedded profile before dropping it
# keeps the colours; dropping it without converting would shift them.
clean_avatar() {  # src dst -> sha256 of dst
  python3 - "$1" "$2" <<'PY'
import hashlib, io, sys
from PIL import Image, ImageCms
src, dst = sys.argv[1], sys.argv[2]
im = Image.open(src)
if im.size[0] != im.size[1]:
    sys.exit(f"{src} is {im.size[0]}x{im.size[1]}; crop it square first (avatars render square)")
icc = im.info.get("icc_profile")
im = im.convert("RGB")
if icc:
    im = ImageCms.profileToProfile(im, ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                                   ImageCms.createProfile("sRGB"), outputMode="RGB")
clean = Image.new("RGB", im.size)
clean.putdata(list(im.getdata()))
clean.save(dst, format="PNG", optimize=True)
print(hashlib.sha256(open(dst, "rb").read()).hexdigest())
PY
}

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
fail=0
for r in "${ROLES[@]}"; do
  name="$(agent "$r" display_name)"; nip05="$(agent "$r" nip05)"
  about="$(agent "$r" capability)"; pub="$(agent "$r" buzz_pubkey)"
  [[ -n "$pub" ]] || die "$r has no buzz_pubkey in the manifest"
  avsha=""
  if [[ $AVATARS == 1 ]]; then
    [[ -f "$AVDIR/$r.png" ]] || die "no avatar at $AVDIR/$r.png"
    avsha="$(clean_avatar "$AVDIR/$r.png" "$TMP/$r.png")"
    scp -q "$TMP/$r.png" "$r@spark:.avatar-sync.png"
  fi
  env_line="$(printf 'NAME=%q NIP05=%q ABOUT=%q EXPECT_PUB=%q AVSHA=%q DRY=%q' "$name" "$nip05" "$about" "$pub" "$avsha" "$DRY")"
  if ! ssh "$r@spark" "$env_line bash -s" <<'REMOTE'; then fail=1; fi
set -euo pipefail
. /opt/nostromo/runtime/env.sh
M=/opt/nostromo/nostromo-src/crew/manifest.yaml
me="$(id -un)"
export BUZZ_RELAY_URL="$(python3 -c 'import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))["relay"]["url"])' "$M")"
export BUZZ_AUTH_TAG="$(python3 -c 'import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))["agents"][sys.argv[2]]["buzz_auth_tag"])' "$M" "$me")"
export BUZZ_PRIVATE_KEY="$(cat ~/.config/nostromo/secrets/buzz.key)"
W="$(mktemp -d)"; trap 'rm -rf "$W" ~/.avatar-sync.png' EXIT
snap() { buzz users get > "$W/p.json"; }   # one relay read; get() only parses it
get() { python3 -c 'import json,sys
d = json.load(open(sys.argv[1])); d = d[0] if isinstance(d, list) else d
print(d.get(sys.argv[2]) or "")' "$W/p.json" "$1"; }

snap
[ "$(get pubkey)" = "$EXPECT_PUB" ] || { echo "$me: this account's key is $(get pubkey | cut -c1-16)…, the manifest says ${EXPECT_PUB:0:16}… — refusing"; exit 1; }
args=()
[ "$(get display_name)" = "$NAME" ]  || args+=(--name "$NAME")
[ "$(get nip05)" = "$NIP05" ]        || args+=(--nip05 "$NIP05")
[ "$(get about)" = "$ABOUT" ]        || args+=(--about "$ABOUT")
if [ -n "$AVSHA" ]; then
  case "$(get picture)" in
    *"$AVSHA"*) ;;
    *) if [ "$DRY" = 1 ]; then args+=(--avatar "<upload $AVSHA>"); else
         up="$(buzz upload file --file ~/.avatar-sync.png)"
         sha="$(printf '%s' "$up" | python3 -c 'import json,sys; print(json.load(sys.stdin)["sha256"])')"
         [ "$sha" = "$AVSHA" ] || { echo "$me: relay stored $sha, expected $AVSHA"; exit 1; }
         args+=(--avatar "$(printf '%s' "$up" | python3 -c 'import json,sys; print(json.load(sys.stdin)["url"])')")
       fi ;;
  esac
fi
if [ ${#args[@]} -eq 0 ]; then echo "$(printf '%-8s' "$me") in line, nothing published"; exit 0; fi
if [ "$DRY" = 1 ]; then echo "$(printf '%-8s' "$me") would set: ${args[*]}"; exit 0; fi
buzz users set-profile "${args[@]}" >/dev/null
snap
bad=""
[ "$(get display_name)" = "$NAME" ] || bad+=" display_name"
[ "$(get nip05)" = "$NIP05" ]       || bad+=" nip05"
[ "$(get about)" = "$ABOUT" ]       || bad+=" about"
[ -z "$AVSHA" ] || case "$(get picture)" in *"$AVSHA"*) ;; *) bad+=" picture" ;; esac
[ -z "$bad" ] || { echo "$me: read back wrong:$bad"; exit 1; }
echo "$(printf '%-8s' "$me") published: $(printf '%s ' "${args[@]}" | sed -E 's#https://[^ ]*/media/([0-9a-f]{12})[0-9a-f]*[^ ]*#…/\1…#')"
REMOTE
done
[[ $fail == 0 ]] || die "one or more roles failed; see above"
