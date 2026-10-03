#!/usr/bin/env bash
# Sign a subscription-backed crew role in to its provider, once. From the Mac, in a terminal — the
# owner runs it; it is interactive by nature, so nothing else does.
#
#   sign-in.sh <role>        e.g. sign-in.sh ash
#
# Codex roles (provider chatgpt): Codex's ChatGPT sign-in finishes by redirecting the browser to
# http://localhost:1455 on the machine running Codex — the Spark, which has no browser. So this opens
# an SSH tunnel from the Mac's port 1455 to the Spark's, runs `codex login` as the role there, and the
# owner opens the URL it prints in the Mac's browser. The sign-in lands in the role's own
# ~/.codex/auth.json (600, in its 700 home); Codex refreshes it after that, and launch-role.sh only
# checks that it is there.
#
# Afterwards: `codex login status` as the role should say it is logged in with ChatGPT. Check the
# subscription's data controls in ChatGPT's settings — whether conversations are used for training.
set -euo pipefail
ROLE="${1:?usage: sign-in.sh <role>}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
read -r HARNESS PROVIDER < <(python3 -c 'import yaml,sys
a = yaml.safe_load(open(sys.argv[1]))["agents"][sys.argv[2]]; print(a["harness"], a["provider"])' \
  "$ROOT/crew/manifest.yaml" "$ROLE")
CODEX=/opt/nostromo/runtime/npm/lib/node_modules/@agentclientprotocol/codex-acp/node_modules/@openai/codex-linux-arm64/vendor/aarch64-unknown-linux-musl/bin/codex

case "$HARNESS/$PROVIDER" in
  codex-acp/chatgpt)
    if lsof -nP -iTCP:1455 -sTCP:LISTEN >/dev/null 2>&1; then
      echo "sign-in: something on this Mac already listens on port 1455; close it first" >&2; exit 1
    fi
    cat <<MSG
== signing $ROLE in to ChatGPT through a tunnel (Mac :1455 -> spark :1455)
   1. Codex prints a sign-in URL below. Open it in a browser on this Mac.
   2. Sign in with the ChatGPT account whose subscription $ROLE should use, and approve.
   3. The browser lands on localhost:1455; the tunnel carries that to the Spark, and Codex says
      it is logged in. Then this exits.
MSG
    ssh -t -o ExitOnForwardFailure=yes -L 1455:localhost:1455 "$ROLE@spark" "$CODEX login"
    echo "== check:"
    ssh "$ROLE@spark" "$CODEX login status; stat -c '%a %n' ~/.codex/auth.json"
    ;;
  *)
    echo "sign-in: $ROLE runs $HARNESS with provider $PROVIDER — no sign-in procedure for that yet" >&2
    exit 1
    ;;
esac
