#!/usr/bin/env bash
# Install the Nostromo runtime base on the Spark (Bootstrap Plan §11.3, §11.10).
#
# Runs ON the Spark, as whichever user the crew runs as, and installs entirely into that user's
# home. No sudo, nothing system-wide, nothing shared with the owner's SquadOps environment.
# Idempotent: re-running verifies what is present and installs only what is missing or moved.
#
# Everything is pinned in versions.lock beside this script. Node and uv publish checksums and are
# verified against them. Herdr publishes a bare binary, so its sha256 is pinned in versions.lock
# on first install and verified on every install after — a first run records, later runs enforce.
#
# Usage: install-base.sh [--check]     --check verifies and installs nothing
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCK="$HERE/versions.lock"
# Default to the real deployment root rather than $HOME. Run once without NOSTROMO_RUNTIME set,
# the old default quietly built a complete second runtime — node, uv, herdr, opencode, 720 MB —
# under the invoking user's home, reported success, and left /opt/nostromo/runtime untouched. The
# harness it was asked to install was installed, in a place nothing looks.
ROOT="${NOSTROMO_RUNTIME:-/opt/nostromo/runtime}"
BIN="$ROOT/bin"
CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1
echo "install-base: runtime root $ROOT" >&2

# shellcheck disable=SC1090
source "$LOCK"

arch="$(uname -m)"
[[ "$arch" == "aarch64" ]] || { echo "this script targets aarch64; found $arch" >&2; exit 1; }
[[ "$(uname -s)" == "Linux" ]] || { echo "this script targets Linux" >&2; exit 1; }

mkdir -p "$ROOT" "$BIN" "$ROOT/dl"
say() { printf '==> %s\n' "$*"; }
have() { [[ -x "$BIN/$1" ]]; }

verify_sha() {  # verify_sha <file> <expected>
  local actual
  actual="$(sha256sum "$1" | awk '{print $1}')"
  [[ "$actual" == "$2" ]] || { echo "sha256 mismatch for $1: got $actual want $2" >&2; exit 1; }
}

# --- Node -------------------------------------------------------------------------------------
# Pinned rather than managed by a version manager: one fewer moving part, and the launcher needs a
# path that does not change under it. claude-agent-acp requires >= 22, which is the binding
# constraint; the pin is the current LTS line.
node_dir="$ROOT/node-${NODE_VERSION}-linux-arm64"
if [[ ! -x "$node_dir/bin/node" ]]; then
  [[ $CHECK_ONLY == 1 ]] && { echo "MISSING node ${NODE_VERSION}"; exit 1; }
  say "installing node ${NODE_VERSION}"
  tar_name="node-${NODE_VERSION}-linux-arm64.tar.xz"
  curl -fsSL -o "$ROOT/dl/$tar_name" "https://nodejs.org/dist/${NODE_VERSION}/${tar_name}"
  curl -fsSL -o "$ROOT/dl/SHASUMS256.txt" "https://nodejs.org/dist/${NODE_VERSION}/SHASUMS256.txt"
  want="$(awk -v n="$tar_name" '$2==n {print $1}' "$ROOT/dl/SHASUMS256.txt")"
  [[ -n "$want" ]] || { echo "no checksum published for $tar_name" >&2; exit 1; }
  verify_sha "$ROOT/dl/$tar_name" "$want"
  tar -xJf "$ROOT/dl/$tar_name" -C "$ROOT"
  rm -f "$ROOT/dl/$tar_name"
fi
ln -sfn "$node_dir/bin/node" "$BIN/node"
ln -sfn "$node_dir/bin/npm"  "$BIN/npm"
ln -sfn "$node_dir/bin/npx"  "$BIN/npx"

export PATH="$BIN:$node_dir/bin:$PATH"

# --- uv ---------------------------------------------------------------------------------------
if [[ "$("$BIN/uv" --version 2>/dev/null | awk '{print $2}')" != "$UV_VERSION" ]]; then
  [[ $CHECK_ONLY == 1 ]] && { echo "MISSING uv ${UV_VERSION}"; exit 1; }
  say "installing uv ${UV_VERSION}"
  base="https://github.com/astral-sh/uv/releases/download/${UV_VERSION}"
  curl -fsSL -o "$ROOT/dl/uv.tar.gz"        "$base/uv-aarch64-unknown-linux-gnu.tar.gz"
  curl -fsSL -o "$ROOT/dl/uv.tar.gz.sha256" "$base/uv-aarch64-unknown-linux-gnu.tar.gz.sha256"
  verify_sha "$ROOT/dl/uv.tar.gz" "$(awk '{print $1}' "$ROOT/dl/uv.tar.gz.sha256")"
  tar -xzf "$ROOT/dl/uv.tar.gz" -C "$ROOT/dl"
  install -m 755 "$ROOT/dl/uv-aarch64-unknown-linux-gnu/uv"  "$BIN/uv"
  install -m 755 "$ROOT/dl/uv-aarch64-unknown-linux-gnu/uvx" "$BIN/uvx"
  rm -rf "$ROOT/dl/uv.tar.gz" "$ROOT/dl/uv.tar.gz.sha256" "$ROOT/dl/uv-aarch64-unknown-linux-gnu"
fi

# --- Herdr ------------------------------------------------------------------------------------
# Upstream ships a bare binary with no published checksum. Record on first install, enforce after.
if [[ "$("$BIN/herdr" --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)" \
      != "${HERDR_VERSION#v}" ]]; then
  [[ $CHECK_ONLY == 1 ]] && { echo "MISSING herdr ${HERDR_VERSION}"; exit 1; }
  say "installing herdr ${HERDR_VERSION}"
  curl -fsSL -o "$ROOT/dl/herdr" \
    "https://github.com/herdrdev/herdr/releases/download/${HERDR_VERSION}/herdr-linux-aarch64"
  got="$(sha256sum "$ROOT/dl/herdr" | awk '{print $1}')"
  if [[ -n "${HERDR_SHA256:-}" ]]; then
    verify_sha "$ROOT/dl/herdr" "$HERDR_SHA256"
  else
    echo "NOTE: no HERDR_SHA256 in versions.lock. Record this and commit it:"
    echo "      HERDR_SHA256=$got"
  fi
  install -m 755 "$ROOT/dl/herdr" "$BIN/herdr"
  rm -f "$ROOT/dl/herdr"
fi

# --- OpenCode ---------------------------------------------------------------------------------
# Installed through npm into a prefix under this root so it cannot reach a shared global.
if [[ "$("$BIN/opencode" --version 2>/dev/null | tr -d '[:space:]')" != "$OPENCODE_VERSION" ]]; then
  [[ $CHECK_ONLY == 1 ]] && { echo "MISSING opencode ${OPENCODE_VERSION}"; exit 1; }
  say "installing opencode ${OPENCODE_VERSION}"
  npm_config_prefix="$ROOT/npm" "$node_dir/bin/npm" install -g --no-fund --no-audit \
    "opencode-ai@${OPENCODE_VERSION}"
  ln -sfn "$ROOT/npm/bin/opencode" "$BIN/opencode"
fi

# --- claude-agent-acp -------------------------------------------------------------------------
# Dallas's harness. Pinned like everything else: an ACP adapter changing underneath a review role
# is a change to what review means. Version-checked separately from OpenCode — nesting it inside
# OpenCode's block meant it silently never installed once OpenCode was already current.
if [[ "$("$BIN/claude-agent-acp" --version 2>/dev/null | tr -d '[:space:]')" != "$CLAUDE_AGENT_ACP_VERSION" ]]; then
  [[ $CHECK_ONLY == 1 ]] && { echo "MISSING claude-agent-acp ${CLAUDE_AGENT_ACP_VERSION}"; exit 1; }
  say "installing claude-agent-acp ${CLAUDE_AGENT_ACP_VERSION}"
  npm_config_prefix="$ROOT/npm" "$node_dir/bin/npm" install -g --no-fund --no-audit \
    "@agentclientprotocol/claude-agent-acp@${CLAUDE_AGENT_ACP_VERSION}"
  ln -sfn "$ROOT/npm/bin/claude-agent-acp" "$BIN/claude-agent-acp"
fi

# --- codex-acp --------------------------------------------------------------------------------
# Ripley's and Parker's harness, pinned for the same reason as the rest: an ACP adapter changing
# underneath an implementation role changes what "the accepted design was built" means.
if [[ "$("$BIN/codex-acp" --version 2>/dev/null | tr -d '[:space:]')" != "$CODEX_ACP_VERSION" ]]; then
  [[ $CHECK_ONLY == 1 ]] && { echo "MISSING codex-acp ${CODEX_ACP_VERSION}"; exit 1; }
  say "installing codex-acp ${CODEX_ACP_VERSION}"
  npm_config_prefix="$ROOT/npm" "$node_dir/bin/npm" install -g --no-fund --no-audit \
    "@agentclientprotocol/codex-acp@${CODEX_ACP_VERSION}"
  ln -sfn "$ROOT/npm/bin/codex-acp" "$BIN/codex-acp"
fi

# --- gh ----------------------------------------------------------------------------------------
# Every role that touches GitHub goes through this, so it belongs in the lockfile like everything
# else. It was the exception: the distro package, unpinned, and old enough that `pr view --json`
# had no `baseRefOid` — which stopped a review mid-flight. Installed under this root so it also
# stops depending on what apt happens to hold.
if [[ "$("$BIN/gh" --version 2>/dev/null | awk 'NR==1{print $3}')" != "$GH_VERSION" ]]; then
  [[ $CHECK_ONLY == 1 ]] && { echo "MISSING gh ${GH_VERSION}"; exit 1; }
  say "installing gh ${GH_VERSION}"
  base="https://github.com/cli/cli/releases/download/v${GH_VERSION}"
  tar_name="gh_${GH_VERSION}_linux_arm64.tar.gz"
  curl -fsSL -o "$ROOT/dl/$tar_name" "$base/$tar_name"
  curl -fsSL -o "$ROOT/dl/gh_checksums.txt" "$base/gh_${GH_VERSION}_checksums.txt"
  want="$(awk -v n="$tar_name" '$2==n {print $1}' "$ROOT/dl/gh_checksums.txt")"
  [[ -n "$want" ]] || { echo "no checksum published for $tar_name" >&2; exit 1; }
  verify_sha "$ROOT/dl/$tar_name" "$want"
  tar -xzf "$ROOT/dl/$tar_name" -C "$ROOT/dl"
  install -m 755 "$ROOT/dl/gh_${GH_VERSION}_linux_arm64/bin/gh" "$BIN/gh"
  rm -rf "$ROOT/dl/$tar_name" "$ROOT/dl/gh_checksums.txt" "$ROOT/dl/gh_${GH_VERSION}_linux_arm64"
fi

# --- crewctl ----------------------------------------------------------------------------------
# Ships in the repo rather than being installed, so a symlink keeps it tracking whatever is
# checked out instead of going stale behind a copy. Unconditional: it has no version to compare.
ln -sfn /opt/nostromo/nostromo-src/infrastructure/spark/bin/crewctl "$BIN/crewctl"

# --- the environment the launcher and the owner both source ------------------------------------
cat > "$ROOT/env.sh" <<EOF
# Written by install-base.sh. Source this to put the Nostromo runtime on PATH.
export NOSTROMO_RUNTIME="$ROOT"
export PATH="$BIN:\$PATH"
export npm_config_prefix="$ROOT/npm"
# The shared repo at /opt/nostromo/nostromo-src is read-only configuration every role reads. Without
# this, running a script from it leaves a __pycache__ owned by whichever role ran first — which is
# how that tree was found to be group-writable at all.
export PYTHONDONTWRITEBYTECODE=1
EOF
chmod 644 "$ROOT/env.sh"

say "installed under $ROOT"
printf '%-10s %s\n' \
  node     "$("$BIN/node" --version)" \
  npm      "$("$BIN/npm" --version)" \
  uv       "$("$BIN/uv" --version)" \
  herdr    "$("$BIN/herdr" --version 2>&1 | head -1)" \
  opencode "$("$BIN/opencode" --version 2>&1 | head -1)"
