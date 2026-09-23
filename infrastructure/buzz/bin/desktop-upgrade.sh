#!/usr/bin/env bash
# Upgrade Buzz Desktop on the owner's Mac: verified before it replaces anything, reversible after.
#
#   desktop-upgrade.sh prepare <version>   download, check the digest, verify the app inside the image.
#                                          Changes nothing; Buzz may stay open.
#   desktop-upgrade.sh install <version>   quit Buzz, back up app and data, swap in the verified app,
#                                          relaunch, verify.
#   desktop-upgrade.sh verify              the installed app is Block's and no agent came back. Works
#                                          after any update path, the in-app button included.
#   desktop-upgrade.sh rollback            quit Buzz, restore the previous app and data from the latest
#                                          backup, relaunch, verify. Moves the current copy aside; deletes nothing.
#
# Why not the in-app Update button: it is sound — it checks a minisign key built into the installed
# app — but it replaces the only working copy and leaves nothing to roll back to, and releases migrate
# data on first launch, so a rollback needs the old app AND the pre-upgrade data.
#
# The trust anchor is Apple, not GitHub: the app must be signed by Block's Team ID and notarized.
# The GitHub digest comes from the same place as the download, so it proves only that the bytes
# arrived intact. It is still worth having: it is the hash docs/source-baseline.md records.
#
# Quitting uses SIGTERM, not an AppleScript quit. AppleScript would need a one-time Automation grant
# ("Terminal wants to control Buzz"), which blocks unattended. Buzz handles SIGTERM with the same
# shutdown as Cmd-Q — terminals, managed agents, mesh — (desktop/src-tauri/src/shutdown.rs,
# install_signal_handler, desktop-v0.5.24). The script never escalates to SIGKILL: an app that will
# not exit may be mid-write, and a person should look at it.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/desktop-common.sh"

TEAM_ID=EYF346PHUG      # Block, Inc.
REPO=block/buzz
WORK="$HOME/.nostromo/buzz-desktop"
BACKUPS="$HOME/.nostromo/backups/buzz-desktop"
SETTLE="${BUZZ_VERIFY_SETTLE:-30}"   # seconds after launch before looking for provisioned agents
MNT=""

die() { echo "error: $*" >&2; exit 1; }
say() { echo "== $*"; }
sha() { shasum -a 256 "$1" | cut -d' ' -f1; }
stamp() { date -u +%Y%m%dT%H%M%SZ; }
plist() { /usr/libexec/PlistBuddy -c "Print :$2" "$1/Contents/Info.plist" 2>/dev/null; }  # not `defaults`: cfprefsd caches
installed_version() { plist "$BUZZ_APP" CFBundleShortVersionString || echo none; }
newer() { python3 -c 'import sys; v=lambda s: tuple(int(x) for x in s.split("."))
sys.exit(0 if sys.argv[2] == "none" or v(sys.argv[1]) > v(sys.argv[2]) else 1)' "$1" "$2"; }
asset_name() {
  case "$(uname -m)" in arm64) echo "Buzz_$1_aarch64.dmg" ;; x86_64) echo "Buzz_$1_x64.dmg" ;; *) die "unknown arch $(uname -m)" ;; esac
}

detach() { [[ -n "$MNT" ]] && { hdiutil detach -quiet "$MNT" 2>/dev/null; rmdir "$MNT" 2>/dev/null; }; MNT=""; }
trap detach EXIT
mount_dmg() {
  MNT="$(mktemp -d /tmp/buzz-dmg.XXXXXX)"
  hdiutil attach -nobrowse -readonly -noautoopen -quiet -mountpoint "$MNT" "$1" || die "cannot mount $1"
  [[ -d "$MNT/Buzz.app" ]] || die "$1 holds no Buzz.app"
}

verify_app() {  # app [expected-version]
  local app="$1" want="${2:-}" got team assess
  [[ "$(plist "$app" CFBundleIdentifier)" == "$BUZZ_BUNDLE_ID" ]] || die "$app is not $BUZZ_BUNDLE_ID"
  got="$(plist "$app" CFBundleShortVersionString)"
  [[ -z "$want" || "$got" == "$want" ]] || die "$app is version $got, expected $want"
  codesign --verify --deep --strict "$app" 2>/dev/null || die "$app: code signature does not verify"
  team="$(codesign -dv "$app" 2>&1 | sed -n 's/^TeamIdentifier=//p')"
  [[ "$team" == "$TEAM_ID" ]] || die "$app: signed by team '$team', expected $TEAM_ID (Block, Inc.)"
  assess="$(spctl -a -t exec -vv "$app" 2>&1)" || die "$app: Gatekeeper rejects it: $assess"
  grep -q 'source=Notarized Developer ID' <<<"$assess" || die "$app: not notarized: $assess"
  echo "   $got  signed by $team, notarized, Gatekeeper accepts  ($app)"
}

quit_buzz() {
  buzz_running || return 0
  local pid i
  pid="$(pgrep -f "${BUZZ_RUNNING_RE}buzz-desktop" | head -1 || true)"
  [[ -n "$pid" ]] || die "Buzz processes are running but no buzz-desktop to ask: $(pgrep -fl "$BUZZ_RUNNING_RE")"
  say "quitting Buzz Desktop (pid $pid) — anything unsent in the app is lost"
  kill -TERM "$pid"
  for i in $(seq 1 30); do buzz_running || { echo "   exited after ${i}s"; return 0; }; sleep 1; done
  die "Buzz did not exit within 30s; not force-killing it. Still running: $(pgrep -fl "$BUZZ_RUNNING_RE" | tr '\n' ' ')"
}

launch_buzz() {
  local i
  say "launching Buzz Desktop"
  open "$BUZZ_APP"
  for i in $(seq 1 20); do buzz_running && return 0; sleep 1; done
  die "Buzz did not start within 20s"
}

cmd_prepare() {
  local ver="$1" asset dir dmg digest have
  asset="$(asset_name "$ver")"; dir="$WORK/$ver"; dmg="$dir/$asset"
  have="$(installed_version)"
  newer "$ver" "$have" || die "installed is $have and $ver is not newer (going back is 'rollback')"
  digest="$(gh release view "desktop-v$ver" -R "$REPO" --json assets -q ".assets[] | select(.name==\"$asset\") | .digest")"
  [[ "$digest" == sha256:* ]] || die "desktop-v$ver publishes no sha256 digest for $asset"
  digest="${digest#sha256:}"
  mkdir -p "$dir"
  if [[ ! -f "$dmg" || "$(sha "$dmg")" != "$digest" ]]; then
    say "downloading $asset"
    gh release download "desktop-v$ver" -R "$REPO" -p "$asset" -D "$dir" --clobber
  fi
  [[ "$(sha "$dmg")" == "$digest" ]] || die "$asset does not match GitHub's digest $digest"
  echo "   sha256 $digest matches GitHub's digest"
  say "verifying the app inside the image, before anything is replaced"
  mount_dmg "$dmg"; verify_app "$MNT/Buzz.app" "$ver"; detach
  echo "$digest" > "$dir/verified.sha256"
  gh release view "desktop-v$ver" -R "$REPO" --json publishedAt -q '.publishedAt[:10]' > "$dir/published"
  say "ready: $have -> $ver. Release notes: https://github.com/$REPO/releases/tag/desktop-v$ver"
  echo "   next: $0 install $ver   (quits Buzz)"
}

cmd_install() {
  local ver="$1" dir dmg from bk
  dir="$WORK/$ver"; dmg="$dir/$(asset_name "$ver")"
  [[ -f "$dir/verified.sha256" ]] || die "run '$0 prepare $ver' first"
  [[ "$(sha "$dmg")" == "$(cat "$dir/verified.sha256")" ]] || die "$dmg changed since prepare; run prepare again"
  from="$(installed_version)"
  newer "$ver" "$from" || die "installed is $from and $ver is not newer"
  # Copy from the image only after checking it again, so the bytes installed are the bytes verified.
  # Staging sits on the same volume as /Applications, so the swap below is a rename, not a copy.
  mount_dmg "$dmg"; verify_app "$MNT/Buzz.app" "$ver"
  rm -rf "$dir/staged"; mkdir -p "$dir/staged"
  ditto "$MNT/Buzz.app" "$dir/staged/Buzz.app"; detach

  quit_buzz
  bk="$BACKUPS/$(stamp)-$from-to-$ver"; mkdir -p "$bk"
  say "backing up to $bk"
  # APFS clones: instant, and no extra space until the app changes the files. The owner key is in the
  # Keychain, which an app upgrade does not touch, so it is not part of this backup.
  cp -Rc "$BUZZ_SUPPORT" "$bk/support"
  [[ -d "$BUZZ_WEBKIT" ]] && cp -Rc "$BUZZ_WEBKIT" "$bk/webkit"
  echo "$from" > "$bk/from-version"
  mv "$BUZZ_APP" "$bk/Buzz.app"
  mv "$dir/staged/Buzz.app" "$BUZZ_APP" || { mv "$bk/Buzz.app" "$BUZZ_APP"; die "swap failed; $from put back"; }
  say "installed $from -> $ver"
  verify_app "$BUZZ_APP" "$ver"
  launch_buzz
  cmd_verify --just-launched
}

cmd_verify() {
  local fail=0 ver dir
  say "installed app"
  verify_app "$BUZZ_APP"
  if ! buzz_running; then
    echo "   Buzz is not running: checking its files only. Launch it and run verify again to see what it does on start."
  elif [[ "${1:-}" == "--just-launched" ]]; then
    say "waiting ${SETTLE}s for anything Buzz provisions on start"
    sleep "$SETTLE"
  fi
  say "no agents on the Mac (Operating Model §35.4)"
  if pgrep -fl "${BUZZ_RUNNING_RE}(buzz-acp|buzz-agent)"; then echo "   FAIL agent processes running"; fail=1; fi
  # The release migrates built-in persona records, and is_active:false on those same records is what
  # keeps them hidden, so check the flags, not only the identities. A persona active that was not
  # before may also be a new starter the release added: look before deciding it is harmless.
  python3 - "$BUZZ_SUPPORT/agents" <<'PY' || fail=1
import json, pathlib, sys
d = pathlib.Path(sys.argv[1])
load = lambda n: json.load((d / n).open()) if (d / n).exists() else []
bad = []
for a in load("managed-agents.json"):
    if a.get("pubkey"):
        bad.append(f"agent with an identity: {a.get('name')} {a['pubkey'][:12]} relay={a.get('relay_url') or '-'}")
    elif a.get("is_active"):
        bad.append(f"persona active again: {a.get('name')}")
teams = load("teams.json")
for t in (teams.values() if isinstance(teams, dict) else teams):
    if t.get("persona_ids"):
        bad.append(f"team references personas again: {t.get('name')} {t['persona_ids']}")
for b in bad:
    print("   FAIL", b)
if not bad:
    print("   ok: no identities, no active personas, no team members")
sys.exit(1 if bad else 0)
PY
  [[ $fail == 0 ]] || die "verify failed. To go back: $0 rollback"

  ver="$(installed_version)"; dir="$WORK/$ver"
  say "docs/source-baseline.md, Buzz Desktop row"
  if [[ -f "$dir/verified.sha256" ]]; then
    echo "| Buzz Desktop | \`desktop-v$ver\`, \`$(asset_name "$ver")\` sha256 \`$(cat "$dir/verified.sha256")\`, installed at \`/Applications/Buzz.app\` by \`infrastructure/buzz/bin/desktop-upgrade.sh\`. The disk image carries no signature; the app inside is signed and notarized by **Block, Inc., Team ID \`$TEAM_ID\`**, and Gatekeeper accepts it — verified on the mounted image before install and on the installed copy after | \`desktop-v$ver\` ($(cat "$dir/published" 2>/dev/null)) | https://github.com/$REPO/releases | $(date +%Y-%m-%d) on the Mac |"
  else
    echo "   $ver was not installed by this script (no prepare record), so there is no DMG hash to record."
  fi
}

cmd_rollback() {
  local bk cur want aside
  bk="$(ls -1d "$BACKUPS"/*/ 2>/dev/null | tail -1 || true)"; bk="${bk%/}"   # names start with a UTC stamp
  [[ -n "$bk" && -d "$bk/Buzz.app" ]] || die "no backup with an app under $BACKUPS"
  cur="$(installed_version)"; want="$(cat "$bk/from-version")"
  say "rolling back $cur -> $want from $bk"
  verify_app "$bk/Buzz.app" "$want"
  quit_buzz
  aside="$bk/rolled-back-$cur-$(stamp)"; mkdir -p "$aside"
  say "moving the current app and data aside to $aside"
  [[ -d "$BUZZ_APP" ]] && mv "$BUZZ_APP" "$aside/Buzz.app"
  [[ -d "$BUZZ_SUPPORT" ]] && mv "$BUZZ_SUPPORT" "$aside/support"
  [[ -d "$BUZZ_WEBKIT" ]] && mv "$BUZZ_WEBKIT" "$aside/webkit"
  mv "$bk/Buzz.app" "$BUZZ_APP"
  cp -Rc "$bk/support" "$BUZZ_SUPPORT"          # copy, so the backup survives for another attempt
  [[ -d "$bk/webkit" ]] && cp -Rc "$bk/webkit" "$BUZZ_WEBKIT"
  launch_buzz
  cmd_verify --just-launched
}

[[ -z "${2:-}" || "$2" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "version must look like 0.5.24, got '$2'"

case "${1:-}" in
  prepare)  [[ -n "${2:-}" ]] || die "usage: $0 prepare <version>"; cmd_prepare "$2" ;;
  install)  [[ -n "${2:-}" ]] || die "usage: $0 install <version>"; cmd_install "$2" ;;
  verify)   cmd_verify ;;
  rollback) cmd_rollback ;;
  *) sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'; exit 2 ;;
esac
