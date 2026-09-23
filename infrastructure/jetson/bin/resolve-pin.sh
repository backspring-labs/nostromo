#!/usr/bin/env bash
# Resolve a Buzz relay image to the exact pin upstream.lock records, from the Mac.
#
# ghcr publishes only `main`, `latest` and digest tags — no per-commit tags — so the commit an image
# was built from is known only from its OCI revision label. Resolving that by hand is four registry
# calls (index, arm64 child, config blob, label) plus a hash of the compose file at that commit,
# which is exactly where a wrong pin slips in. `latest` is NOT current: on 2026-09-23 it pointed at
# a build from 2026-08-08. Track `main`.
#
# Usage: resolve-pin.sh [main | sha256:<index digest>] [--expect <commit>] [--write]
#   prints the upstream.lock this image implies; --write also rewrites upstream.lock and the
#   BUZZ_IMAGE line in buzz.env. Commit the result, then run bin/upgrade.sh.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOCK="$HERE/buzz/upstream.lock"
ENV="$HERE/buzz/buzz.env"
REPO=block/buzz
REF=main EXPECT="" WRITE=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --expect) EXPECT="$2"; shift 2 ;;
    --write)  WRITE=1; shift ;;
    -*)       echo "unknown flag $1" >&2; exit 2 ;;
    *)        REF="$1"; shift ;;
  esac
done
die() { echo "resolve-pin: $*" >&2; exit 1; }

TOKEN="$(curl -fsS "https://ghcr.io/token?scope=repository:$REPO:pull" | python3 -c 'import json,sys; print(json.load(sys.stdin)["token"])')"
reg() {  # path accept -> body; follows blob redirects
  curl -fsSL -H "Authorization: Bearer $TOKEN" -H "Accept: $2" "https://ghcr.io/v2/$REPO/$1"
}
INDEX_ACCEPT='application/vnd.oci.image.index.v1+json, application/vnd.docker.distribution.manifest.list.v2+json'
MANIFEST_ACCEPT='application/vnd.oci.image.manifest.v1+json, application/vnd.docker.distribution.manifest.v2+json'

TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
reg "manifests/$REF" "$INDEX_ACCEPT" > "$TMP"
# The digest of the bytes we were served, not a header we were told: a pin is only as good as this.
# Hashed from a file, because $(...) strips trailing newlines and would change the digest.
INDEX_DIGEST="sha256:$(shasum -a 256 "$TMP" | cut -d' ' -f1)"
[[ "$REF" != sha256:* || "$REF" == "$INDEX_DIGEST" ]] || die "registry served $INDEX_DIGEST for $REF"
ARM64="$(python3 -c 'import json,sys
m = json.load(open(sys.argv[1]))
a = [x["digest"] for x in m.get("manifests", []) if x.get("platform", {}).get("architecture") == "arm64"]
print(a[0] if a else "")' "$TMP")"
[[ -n "$ARM64" ]] || die "$REF has no linux/arm64 image; the Jetson cannot run it"

# The label is read from the arm64 child, because that is the image the Jetson runs.
CONFIG="$(reg "manifests/$ARM64" "$MANIFEST_ACCEPT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["config"]["digest"])')"
COMMIT="$(reg "blobs/$CONFIG" '*/*' | python3 -c 'import json,sys
l = json.load(sys.stdin)["config"].get("Labels") or {}
print(l.get("org.opencontainers.image.revision", ""))')"
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "arm64 image $ARM64 carries no revision label; cannot tell what it was built from"
[[ -z "$EXPECT" || "$COMMIT" == "$EXPECT"* ]] || die "$REF was built from $COMMIT, not $EXPECT"

COMMIT_DATE="$(gh api "repos/$REPO/commits/$COMMIT" -q '.commit.committer.date[:10]')"
COMPOSE_SHA="$(gh api "repos/$REPO/contents/deploy/compose/compose.yml?ref=$COMMIT" -H 'Accept: application/vnd.github.raw' | shasum -a 256 | cut -d' ' -f1)"

NEW_LOCK="$(cat <<EOF
# Upstream block/buzz assets this deployment is pinned to. install.sh fetches deploy/compose/compose.yml at
# BUZZ_COMMIT and refuses to install if its sha256 differs from the value here. Update every line together,
# and mirror the change in buzz.env (BUZZ_IMAGE) and docs/source-baseline.md. bin/resolve-pin.sh writes it.
BUZZ_COMMIT=$COMMIT
BUZZ_COMMIT_DATE=$COMMIT_DATE
BUZZ_IMAGE_INDEX_DIGEST=$INDEX_DIGEST
BUZZ_IMAGE_ARM64_DIGEST=$ARM64
SHA256_COMPOSE_YML=$COMPOSE_SHA
EOF
)"

# shellcheck disable=SC1090
OLD_COMMIT="$(source "$LOCK" && echo "$BUZZ_COMMIT")"
echo "$NEW_LOCK" | grep -v '^#'
echo
if [[ "$OLD_COMMIT" == "$COMMIT" ]]; then
  echo "== already pinned to ${COMMIT:0:10}"
else
  echo "== ${OLD_COMMIT:0:10} -> ${COMMIT:0:10}: $(gh api "repos/$REPO/compare/$OLD_COMMIT...$COMMIT" -q '"\(.ahead_by) commits ahead, \(.behind_by) behind"')"
  # List the directory at both ends rather than asking the compare API: it returns at most 300 files,
  # so across a large gap it silently omits migrations and an empty list reads as "none". It did,
  # on the first run of this script (c045321a..0cc63fe3, 765 files, four migrations).
  migs() { gh api "repos/$REPO/contents/migrations?ref=$1" -q '.[].name' | grep '\.sql$' | sort; }
  NEW_MIGS="$(comm -13 <(migs "$OLD_COMMIT") <(migs "$COMMIT") | tr '\n' ' ')"
  echo "   new migrations: ${NEW_MIGS:-none}"
  [[ -z "$NEW_MIGS" ]] || echo "   migrations are one-way: rolling back means restoring the pre-upgrade backup (bin/rehearse-upgrade.sh proves it)"
fi

if [[ $WRITE == 1 ]]; then
  echo "$NEW_LOCK" > "$LOCK"
  python3 - "$ENV" "$INDEX_DIGEST" <<'PY'
import pathlib, re, sys
p, digest = pathlib.Path(sys.argv[1]), sys.argv[2]
s, n = re.subn(r"(?m)^BUZZ_IMAGE=ghcr\.io/block/buzz@sha256:[0-9a-f]{64}$", f"BUZZ_IMAGE=ghcr.io/block/buzz@{digest}", p.read_text())
if n != 1:
    sys.exit(f"expected exactly one BUZZ_IMAGE line in {p}, found {n}")
p.write_text(s)
PY
  echo "== wrote $LOCK and BUZZ_IMAGE in $ENV. Update the relay rows in docs/source-baseline.md, commit, then bin/upgrade.sh."
fi
