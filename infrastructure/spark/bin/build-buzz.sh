#!/usr/bin/env bash
# Build the four block/buzz binaries the crew runs — buzz-acp, buzz (the CLI), buzz-agent and
# buzz-dev-mcp — from ONE commit, and install them only after the new build is shown to accept what
# the launcher passes it. No linux-arm64 release is published, so the Spark builds its own. The first
# build (c045321a, 2026-09-15) was done by hand and recorded nowhere but the ledger; this is that
# build, written down.
#
# Runs ON the Spark as the supervisor (nostromo), which owns /opt/nostromo. Run push-repo.sh first,
# so the launcher it checks against is the one that will run.
#
#   build-buzz.sh <commit>             fetch, build, check. Installs nothing
#   build-buzz.sh <commit> --install   ... then back up the running binaries and swap the new ones in
#
# Installing moves no running process onto the new code: each keeps the binary it was started with,
# because the swap is a rename. Restart roles with crewctl afterwards, a canary first.
# Pin the same commit as the relay unless there is a reason not to; the ledger records both.
set -euo pipefail
die() { echo "build-buzz: $*" >&2; exit 1; }
say() { echo "== $*"; }

COMMIT="${1:-}"
[[ "$COMMIT" =~ ^[0-9a-f]{40}$ ]] || die "usage: build-buzz.sh <40-hex commit> [--install]"
INSTALL=0; [[ "${2:-}" == "--install" ]] && INSTALL=1
[[ "$(id -un)" == nostromo ]] || die "run as the supervisor, nostromo — it owns /opt/nostromo"

R=/opt/nostromo/runtime
BIN="$R/bin"
SRC=/opt/nostromo/buzz-src
LAUNCHER=/opt/nostromo/nostromo-src/infrastructure/spark/bin/launch-role.sh
BINS=(buzz buzz-acp buzz-agent buzz-dev-mcp)
export CARGO_HOME="$R/cargo" RUSTUP_HOME="$R/rustup" PATH="$R/cargo/bin:$PATH"
[[ -r "$LAUNCHER" ]] || die "no launcher at $LAUNCHER — run push-repo.sh from the Mac"

RUNNING="$(cat "$BIN/buzz-build.commit" 2>/dev/null || echo unrecorded)"
say "building ${COMMIT:0:10} (running: ${RUNNING:0:10})"
cd "$SRC"
git fetch -q origin "$COMMIT"
git checkout -q --detach "$COMMIT"
[[ "$(git rev-parse HEAD)" == "$COMMIT" ]] || die "checkout did not land on $COMMIT"
start=$SECONDS
cargo build -q --release --locked $(printf -- '--bin %s ' "${BINS[@]}")
echo "   built in $((SECONDS - start))s"

# Gate 1: every flag the launcher hands buzz-acp must exist in the new buzz-acp. A renamed flag
# would not fail here quietly; it would fail every role at start, and systemd would retry forever.
# Read from the new binary's own --help, not from its source.
FLAGS="$( { sed -n '/^exec buzz-acp/,/[^\\]$/p' "$LAUNCHER"; grep -E '_ARGS?=\(' "$LAUNCHER"; } \
          | grep -oE -- '--[a-z][a-z0-9-]+' | sort -u)"
[[ -n "$FLAGS" ]] || die "found no buzz-acp flags in the launcher; the gate would pass vacuously"
HELP="$(target/release/buzz-acp --help)"
missing=""
for f in $FLAGS; do grep -qE -- "(^|[[:space:],])${f}([[:space:]=,]|$)" <<<"$HELP" || missing+=" $f"; done
[[ -z "$missing" ]] || die "the new buzz-acp does not accept:$missing"
echo "   buzz-acp accepts all $(wc -w <<<"$FLAGS") launcher flags"

# Gate 2: every BUZZ_* variable the launcher exports must be read by one of the new binaries.
VARS="$(grep -oE 'export (BUZZ|OPENAI_COMPAT)_[A-Z0-9_]+' "$LAUNCHER" | awk '{print $2}' | sort -u)"
missing=""
for v in $VARS; do
  found=0
  for b in "${BINS[@]}"; do grep -aq -- "$v" "target/release/$b" && { found=1; break; }; done
  [[ $found == 1 ]] || missing+=" $v"
done
[[ -z "$missing" ]] || die "no new binary reads:$missing"
echo "   the new binaries read all $(wc -w <<<"$VARS") variables the launcher exports"

if [[ $INSTALL == 0 ]]; then
  say "checked, not installed. Next: build-buzz.sh $COMMIT --install"
  exit 0
fi

BK="/opt/nostromo/backups/buzz-bin/$(date -u +%Y%m%dT%H%M%SZ)-${RUNNING:0:10}"
mkdir -p "$BK"
for b in "${BINS[@]}"; do cp -p "$BIN/$b" "$BK/"; done
(cd "$BK" && sha256sum "${BINS[@]}" > SHA256SUMS)
echo "$RUNNING" > "$BK/commit"
say "backed up the running binaries to $BK"
for b in "${BINS[@]}"; do
  install -m 755 "target/release/$b" "$BIN/.$b.new"
  mv -f "$BIN/.$b.new" "$BIN/$b"
done
echo "$COMMIT" > "$BIN/buzz-build.commit"
(cd "$BIN" && sha256sum "${BINS[@]}") > "$BIN/buzz-build.sha256"
say "installed ${COMMIT:0:10}; no role runs it until restarted"
echo "   canary: crewctl restart mother, then the rest"
echo "   rollback: cp -p $BK/{buzz,buzz-acp,buzz-agent,buzz-dev-mcp} $BIN/ && echo $RUNNING > $BIN/buzz-build.commit, then restart"
