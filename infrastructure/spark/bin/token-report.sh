#!/usr/bin/env bash
# What a metered Codex role's turns cost, in tokens, from its own session logs. From the Mac.
#
#   token-report.sh <role> [--since YYYY-MM-DD] [--turns] [--usd IN,CACHED,OUT]
#
#   --since   sessions with activity on or after this date (default: seven days ago)
#   --turns   one row per turn, labelled with who asked and what — the per-review cost
#   --usd     override the prices, per million tokens: IN,CACHED,OUT[,CACHE_WRITE]
#
# Dollars come from crew/prices.yaml for the role's model (crew/manifest.yaml), priced call by call
# so a long-context surcharge lands only on the calls that exceeded it. Every run prints where and
# when the prices were checked, and warns once they are stale: an estimate, not the provider's bill.
#
# Codex writes every model call's usage to ~/.codex/sessions/**/rollout-*.jsonl. Each call re-sends
# the session so far, so cost tracks calls x context, not the length of the answer: "peak ctx" is
# the largest context one call re-sent, "big out" the largest tool output that then rode along on
# every later call. Codex roles only (Ripley, Parker); Dallas runs Claude Code, whose logs differ.
#
# Reads as the role (ssh <role>@spark): the logs live in its 700 home, and nothing is copied off.
set -euo pipefail
ROLE="${1:-}"; [[ -n "$ROLE" && "$ROLE" != -* ]] || { sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
shift
SINCE="$(date -u -v-7d +%F 2>/dev/null || date -u -d '7 days ago' +%F)"; TURNS=0; USD=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --since) SINCE="${2:?--since needs a date}"; shift 2 ;;
    --turns) TURNS=1; shift ;;
    --usd)   USD="${2:?--usd needs IN,CACHED,OUT}"; shift 2 ;;
    *)       echo "unknown argument $1" >&2; exit 2 ;;
  esac
done
[[ "$SINCE" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "--since wants YYYY-MM-DD" >&2; exit 2; }
[[ -z "$USD" || "$USD" =~ ^[0-9.]+,[0-9.]+,[0-9.]+(,[0-9.]+)?$ ]] \
  || { echo "--usd wants IN,CACHED,OUT or IN,CACHED,OUT,CACHE_WRITE" >&2; exit 2; }

ssh "$ROLE@spark" "python3 - '$ROLE' '$SINCE' '$TURNS' '$USD'" <<'PY'
import datetime, glob, json, os, re, sys
import yaml

role, since, show_turns, usd = sys.argv[1], sys.argv[2], sys.argv[3] == "1", sys.argv[4]
REPO = "/opt/nostromo/nostromo-src/crew"
model = yaml.safe_load(open(f"{REPO}/manifest.yaml"))["agents"].get(role, {}).get("model", "?")
price, note = None, ""
if usd:
    v = [float(x) for x in usd.split(",")]
    price = {"input": v[0], "cached_input": v[1], "output": v[2], "cache_write": v[3] if len(v) > 3 else v[0] * 1.25}
    note = f"prices from --usd for {model}"
else:
    try: price = yaml.safe_load(open(f"{REPO}/prices.yaml"))["models"].get(model)
    except FileNotFoundError: price = None
    if price:
        today = datetime.date.today()
        checked, promo = price.get("checked"), price.get("promotional_until")
        note = (f"prices for {model}: ${price['input']:.2f} input, ${price['cached_input']:.2f} cached, "
                f"${price['cache_write']:.2f} cache write, ${price['output']:.2f} output per 1M tokens; "
                f"checked {checked} at {price.get('source', '?')}")
        if promo: note += f"; promotional until {promo}"
        if (checked and (today - checked).days > 45) or (promo and today > promo):
            note += "\n  WARNING: these prices are stale — re-check them and update crew/prices.yaml"
    else:
        note = f"no price for {model} in crew/prices.yaml, so no dollars"
files = sorted(glob.glob(os.path.expanduser("~/.codex/sessions/*/*/*/rollout-*.jsonl")))
cutoff = datetime.datetime.fromisoformat(since).timestamp()
files = [f for f in files if os.path.getmtime(f) >= cutoff]
if not files:
    print(f"no Codex sessions since {since} in ~/.codex/sessions"); sys.exit(0)

def blank(label=""):
    return {"label": label, "calls": 0, "input": 0, "cached": 0, "write": 0, "output": 0, "reasoning": 0,
            "peak": 0, "big_out": 0, "compactions": 0, "usd": 0.0}

def call_cost(u):
    if not price: return 0.0
    inp, cached = u.get("input_tokens", 0), u.get("cached_input_tokens", 0)
    write = u.get("cache_write_input_tokens", 0) or 0
    plain = max(inp - cached - write, 0)
    xi = xo = 1.0
    if price.get("long_context_over") and inp > price["long_context_over"]:
        xi, xo = price.get("long_context_input_x", 1.0), price.get("long_context_output_x", 1.0)
    return ((plain * price["input"] + cached * price["cached_input"] + write * price["cache_write"]) * xi
            + u.get("output_tokens", 0) * price["output"] * xo) / 1e6

def add(acc, usage):
    acc["calls"] += 1
    acc["input"] += usage.get("input_tokens", 0)
    acc["cached"] += usage.get("cached_input_tokens", 0)
    acc["write"] += usage.get("cache_write_input_tokens", 0) or 0
    acc["usd"] += call_cost(usage)
    acc["output"] += usage.get("output_tokens", 0)
    acc["reasoning"] += usage.get("reasoning_output_tokens", 0)
    acc["peak"] = max(acc["peak"], usage.get("input_tokens", 0))

def dollars(a):
    return f"  ${a['usd']:6.2f}" if price else ""

def k(n): return f"{n/1000:,.0f}K" if n >= 1000 else str(n)

def row(a):
    pct = f"{100 * a['cached'] / a['input']:.0f}%" if a["input"] else "-"
    return (f"{a['calls']:>5}  {k(a['input']):>7}  {pct:>4}  {k(a['output']):>6}  {k(a['reasoning']):>6}"
            f"  {k(a['peak']):>6}  {k(a['big_out']):>6}  {a['compactions']:>4}{dollars(a)}")

HEAD = (f"{'calls':>5}  {'input':>7}  {'cach':>4}  {'output':>6}  {'reason':>6}  {'peak':>6}  {'big':>6}  {'cmpt':>4}"
        + ("  est.$" if price else ""))
total = blank()
print(f"{role} — {note}\n")
print(f"{'':42}{HEAD}")
print(f"{'':42}{'':>5}  {'tokens':>7}  {'ed':>4}  {'':>6}  {'':>6}  {'ctx':>6}  {'out*':>6}")
for f in files:
    sess = blank(); turns = []; cur = None
    for line in open(f, errors="replace"):
        try: d = json.loads(line)
        except ValueError: continue
        t, p = d.get("type"), d.get("payload") or {}
        if not isinstance(p, dict): p = {}
        if t == "compacted":
            for a in (sess, cur):
                if a is not None: a["compactions"] += 1
        elif t == "response_item" and p.get("type") == "message" and p.get("role") == "user":
            txt = " ".join(x.get("text", "") for x in (p.get("content") or []) if isinstance(x, dict))
            if "<buzz-event" in txt:  # the first turn arrives bundled with the base prompt
                ev = txt[txt.rfind("<buzz-event"):]
                who = re.search(r"From: (\S+)", ev); what = re.search(r"Content: (.*?)\n", ev)
                when = (d.get("timestamp") or "")[5:16].replace("T", " ")
                label = f"{when} {who.group(1) if who else '?'}: {(what.group(1) if what else '').strip()}"
                cur = blank(label[:40]); turns.append(cur)
        elif t == "response_item" and p.get("type") in ("custom_tool_call_output", "function_call_output"):
            o = p.get("output"); size = len(o if isinstance(o, str) else json.dumps(o))
            for a in (sess, cur):
                if a is not None: a["big_out"] = max(a["big_out"], size // 4)  # ~4 chars a token
        elif t == "event_msg" and p.get("type") == "token_count" and p.get("info"):
            u = p["info"].get("last_token_usage") or {}
            add(sess, u)
            if cur is not None: add(cur, u)
    start = os.path.basename(f)[8:24].replace("T", " ")
    sess["label"] = f"session {start}, {len(turns)} turn{'s' if len(turns) != 1 else ''}"
    print(f"{sess['label']:42}{row(sess)}")
    if show_turns:
        for tr in turns: print(f"  {tr['label']:40}{row(tr)}")
    for key in ("calls", "input", "cached", "write", "output", "reasoning", "compactions", "usd"): total[key] += sess[key]
    total["peak"] = max(total["peak"], sess["peak"]); total["big_out"] = max(total["big_out"], sess["big_out"])
print(f"{'total since ' + since:42}{row(total)}")
print("\n* big out: the largest tool output, in tokens (about 4 characters each), re-sent on every later call.")
PY
