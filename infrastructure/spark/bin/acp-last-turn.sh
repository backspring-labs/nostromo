#!/usr/bin/env bash
# Summarise the most recent turn from a role's ACP capture.
#
# buzz-acp logs a turn's start and its outcome and nothing in between, and an ACP adapter can fail a
# tool call without saying so anywhere a person will look: the agent is told "denied", finishes the
# turn reporting success, and buzz-acp records outcome="ok". The capture is the only witness, and it
# lives under a role's 700 log directory, so reading it means root either way. This makes that one
# command instead of a shell-quoting exercise at 2am.
#
#   sudo acp-last-turn.sh <role> [--turns N] [--raw]
#
# Requires NOSTROMO_ACP_TRACE=1 on the role (infrastructure/spark/systemd/, trace.conf drop-in).
set -euo pipefail

ROLE="${1:?usage: acp-last-turn.sh <role> [--turns N] [--raw]}"; shift
TURNS=1; RAW=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --turns) TURNS="${2:?--turns needs a count}"; shift 2 ;;
    --raw)   RAW=1; shift ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done

DIR="/opt/nostromo/logs/$ROLE/acp"
[[ -d "$DIR" ]] || { echo "no capture directory $DIR — is NOSTROMO_ACP_TRACE=1 set for $ROLE?" >&2; exit 1; }

if [[ $RAW == 1 ]]; then
  exec tail -n 200 "$(ls -t "$DIR"/*.jsonl | head -1)"
fi

python3 - "$DIR" "$TURNS" <<'PY'
import glob, json, os, sys

directory, turns = sys.argv[1], int(sys.argv[2])
files = sorted(glob.glob(os.path.join(directory, "*.jsonl")), key=os.path.getmtime, reverse=True)
if not files:
    sys.exit(f"no .jsonl captures in {directory}")

def clip(value, width=150):
    text = " ".join(str(value).split())
    return text if len(text) <= width else text[: width - 1] + "…"

def text_of(block):
    """Pull readable text out of the several shapes ACP uses for content."""
    if isinstance(block, str):
        return block
    if isinstance(block, dict):
        for key in ("text", "content", "message", "output", "reason", "description"):
            if key in block:
                return text_of(block[key])
    if isinstance(block, list):
        return " ".join(filter(None, (text_of(b) for b in block)))
    return ""

# The two directions are separate files: the client's requests (session/prompt) in one, the
# adapter's replies (session/update, and every tool call) in the other. They are sliced separately
# and merged after. Concatenating them first and slicing from the last session/prompt cut every
# tool call out of the result and reported "none in this turn" for a turn with two — the same
# failure mode as everything else today, an empty answer that looks like a finding.
TAIL = 400
records, read = [], []
for path in files[:4]:
    parsed = []
    with open(path, errors="replace") as handle:
        for line in handle:
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                parsed.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    starts = [i for i, r in enumerate(parsed) if r.get("method") == "session/prompt"]
    if starts:
        kept = parsed[starts[-min(turns, len(starts))]:]
        where = f"from prompt #{len(starts) - min(turns, len(starts)) + 1}"
    else:
        kept = parsed[-TAIL:]
        where = f"tail {len(kept)}" if kept else "empty"
    read.append(f"{os.path.basename(path)} ({len(parsed)} records, {where})")
    records.extend((os.path.basename(path), r) for r in kept)

print("READ     " + "\n         ".join(read) + "\n")
if not records:
    sys.exit("captures are empty — the role may not have taken a turn since the last restart")

calls = {}
for source, record in records:
    method = record.get("method", "")
    params = record.get("params") or {}
    update = params.get("update") or {}
    kind = update.get("sessionUpdate", "")

    if method == "session/prompt":
        prompt = text_of(params.get("prompt"))
        print(f"PROMPT   {clip(prompt, 400)}\n")

    elif kind in ("tool_call", "tool_call_update"):
        call_id = update.get("toolCallId", "?")
        entry = calls.setdefault(call_id, {"title": "", "status": [], "detail": ""})
        entry["title"] = update.get("title") or entry["title"]
        raw = update.get("rawInput") or {}
        command = raw.get("command") or raw.get("cmd") or ""
        if command:
            entry["title"] = f"{entry['title']}  {clip(command, 220)}".strip()
        status = update.get("status")
        if status and (not entry["status"] or entry["status"][-1] != status):
            entry["status"].append(status)
        detail = text_of(update.get("content")) or text_of(update.get("rawOutput"))
        if detail:
            entry["detail"] = clip(detail, 300)

    elif kind == "agent_message_chunk":
        pass  # observer stream only; never delivered, and it is what misleads us

    elif "error" in record:
        error = record["error"]
        print(f"ERROR    {error.get('code', '')} {clip(error.get('message', error))}")

    elif method in ("session/request_permission", "session/set_config_option"):
        print(f"REQUEST  {method}  {clip(params)}")

    elif "stopReason" in (record.get("result") or {}):
        print(f"\nSTOP     {record['result']['stopReason']}")

if calls:
    print("TOOL CALLS")
    for call_id, entry in calls.items():
        flow = " → ".join(entry["status"]) or "no status"
        marker = "✗" if {"denied", "failed", "error"} & set(entry["status"]) else "✓"
        print(f"  {marker} [{flow}] {entry['title'] or call_id}")
        if entry["detail"]:
            print(f"      {entry['detail']}")
else:
    print("TOOL CALLS  none in this turn")
PY
