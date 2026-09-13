#!/usr/bin/env bash
# Install the Nostromo runtime base on the Spark (NOSTROMO-PLAN-0001 §11.3, §11.10).
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
ROOT="${NOSTROMO_RUNTIME:-$HOME/.local/nostromo}"
BIN="$ROOT/bin"
CHECK_ONLY=0
[[ "${1:-}" == "--check" ]] && CHECK_ONLY=1

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

# --- the environment the launcher and the owner both source ------------------------------------
cat > "$ROOT/env.sh" <<EOF
# Written by install-base.sh. Source this to put the Nostromo runtime on PATH.
export NOSTROMO_RUNTIME="$ROOT"
export PATH="$BIN:\$PATH"
export npm_config_prefix="$ROOT/npm"
EOF
chmod 644 "$ROOT/env.sh"

say "installed under $ROOT"
printf '%-10s %s\n' \
  node     "$("$BIN/node" --version)" \
  npm      "$("$BIN/npm" --version)" \
  uv       "$("$BIN/uv" --version)" \
  herdr    "$("$BIN/herdr" --version 2>&1 | head -1)" \
  opencode "$("$BIN/opencode" --version 2>&1 | head -1)"
