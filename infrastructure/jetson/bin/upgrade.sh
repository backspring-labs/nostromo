#!/usr/bin/env bash
# Upgrade the Buzz relay on the Jetson to the pin in upstream.lock, from the Mac.
#
# The order is the point, and each step gates the next:
#   backup on the Jetson -> copy it off-host -> rehearse the migration on THAT copy -> install -> probe
# The rehearsal restores the very backup a rollback would use, so a set that cannot be restored, or
# a migration that fails, stops the upgrade before the Jetson changes. On 2026-09-23 the newest
# off-host copy was two weeks old and predated every identity worth keeping; this makes the copy
# part of the upgrade rather than a step to remember.
#
# Pin first:  bin/resolve-pin.sh main --write, update docs/source-baseline.md, commit.
# Usage:      bin/upgrade.sh [ssh-host]     default: nano
#
# Rollback is deliberately not a script — see "Upgrade and rollback" in ../README.md. It is rare, it
# loses whatever was written after the upgrade, and a person should decide that.
set -euo pipefail
HOST="${1:-nano}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OFFHOST="$HOME/.nostromo/backups/jetson"
die() { echo "upgrade: $*" >&2; exit 1; }
say() { echo "== $*"; }
lockval() { (source "$1" && eval "echo \$$2"); }

# What is deployed must be what the repo records, or the ledger lies about the relay.
git -C "$HERE" diff --quiet HEAD -- . || die "uncommitted changes under infrastructure/jetson — commit the pin first"
PIN="$(lockval "$HERE/buzz/upstream.lock" BUZZ_COMMIT)"
DEPLOYED="$(ssh "$HOST" 'sed -n "s/^BUZZ_COMMIT=//p" /mnt/ssd/buzz/deploy/upstream.lock')"
[[ -n "$DEPLOYED" ]] || die "cannot read the deployed upstream.lock on $HOST"
[[ "$DEPLOYED" != "$PIN" ]] || die "$HOST already runs ${PIN:0:10}; to re-sync config, run bin/install.sh"
say "upgrading $HOST: ${DEPLOYED:0:10} -> ${PIN:0:10}"

say "backup on $HOST"
STAMP="$(ssh "$HOST" /mnt/ssd/buzz/deploy/backup.sh | sed -n 's|^backup: .*/||p')"
[[ "$STAMP" =~ ^[0-9]{8}T[0-9]{6}Z$ ]] || die "backup.sh did not report a set"
say "copying $STAMP off-host"
mkdir -p -m 700 "$OFFHOST/$STAMP"
rsync -a "$HOST:/mnt/ssd/buzz/backups/$STAMP/" "$OFFHOST/$STAMP/"
(cd "$OFFHOST/$STAMP" && shasum -a 256 -c --quiet SHA256SUMS) || die "the off-host copy fails its checksums"
chmod 600 "$OFFHOST/$STAMP"/*
[[ "$(lockval "$OFFHOST/$STAMP/upstream.lock" BUZZ_COMMIT)" == "$DEPLOYED" ]] || die "backup $STAMP was not taken from ${DEPLOYED:0:10}"

say "rehearsing on the copy"
"$HERE/bin/rehearse-upgrade.sh" "$OFFHOST/$STAMP"

say "installing on $HOST — relay and pairing restart; the crew reconnects"
NOSTROMO_RELAY_UPGRADE=1 "$HERE/bin/install.sh" "$HOST"
for _ in $(seq 1 60); do ssh "$HOST" 'curl -fsS -o /dev/null http://127.0.0.1:8080/_readiness' 2>/dev/null && break; sleep 2; done

say "probes"
"$HERE/bin/probe.sh" "$HOST" || die "probes failed after install. Rollback point: $STAMP (README: Upgrade and rollback)"
say "done: ${DEPLOYED:0:10} -> ${PIN:0:10}. Rollback point: $OFFHOST/$STAMP"
echo "   check that the crew answers in #nostromo, and that Buzz Desktop reconnected"
