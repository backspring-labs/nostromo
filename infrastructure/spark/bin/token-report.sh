#!/usr/bin/env bash
# What a metered role's turns cost, in tokens and dollars, from its own session logs. From the Mac.
#
#   token-report.sh <role> [--since YYYY-MM-DD] [--turns] [--usd IN,CACHED,OUT[,CACHE_WRITE]]
#
#   --since   sessions with activity on or after this date (default: seven days ago)
#   --turns   one row per turn, labelled with who asked and what — the per-review cost
#   --usd     override the prices, per million tokens (cache writes default to 1.25x input)
#
# Reads whichever harness the role runs (crew/manifest.yaml):
#   codex-acp         ~/.codex/sessions/**/rollout-*.jsonl    (Ripley, Parker)
#   claude-agent-acp  ~/.claude/projects/*/*.jsonl            (Dallas)
# Every call re-sends the session so far, so cost tracks calls x context, not the length of the
# answer: "peak ctx" is the largest context one call re-sent, "big out" the largest tool output that
# then rode along on every later call. Each session row also names the model the API actually ran —
# which is how Dallas was found running claude-opus-5 while the manifest said claude-opus-5-5.
#
# Dollars come from crew/prices.yaml, priced call by call: by the manifest's model for Codex, by the
# model the API recorded for Claude, with long-context, US-only (1.1x) and fast-mode rates where they
# apply. Every run prints where and when the prices were checked, and warns once they are stale: an
# estimate, not the provider's bill.
#
# Reads as the role (ssh <role>@spark): the logs live in its 700 home, and nothing is copied off.
set -euo pipefail
ROLE="${1:-}"; [[ -n "$ROLE" && "$ROLE" != -* ]] || { sed -n '2,22p' "$0" | sed 's/^# \{0,1\}//'; exit 2; }
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
agent = yaml.safe_load(open(f"{REPO}/manifest.yaml"))["agents"].get(role, {})
harness, pinned = agent.get("harness", "?"), agent.get("model", "?")
try: PRICES = yaml.safe_load(open(f"{REPO}/prices.yaml"))["models"]
except FileNotFoundError: PRICES = {}
OVERRIDE = None
if usd:
    v = [float(x) for x in usd.split(",")]
    OVERRIDE = {"input": v[0], "cached_input": v[1], "output": v[2], "cache_write": v[3] if len(v) > 3 else v[0] * 1.25}
cutoff = datetime.datetime.fromisoformat(since).timestamp()
unpriced = set()

def price_for(model):
    return OVERRIDE or PRICES.get(model)

def call_cost(c):
    p = price_for(c["model"])
    if not p:
        unpriced.add(c["model"]); return 0.0
    xi = xo = 1.0
    if p.get("long_context_over") and c["input"] > p["long_context_over"]:
        xi, xo = p.get("long_context_input_x", 1.0), p.get("long_context_output_x", 1.0)
    if c.get("speed") == "fast":
        xi, xo = xi * p.get("fast_input_x", 2.0), xo * p.get("fast_output_x", 2.0)
    geo = 1.1 if c.get("geo") == "us" else 1.0
    plain = max(c["input"] - c["cached"] - c["write5"] - c["write1h"], 0)
    cost_in = (plain * p["input"] + c["cached"] * p["cached_input"] + c["write5"] * p["cache_write"]
               + c["write1h"] * p.get("cache_write_1h", p["input"] * 2)) * xi
    return geo * (cost_in + c["output"] * p["output"] * xo) / 1e6

def blank(label=""):
    return {"label": label, "calls": 0, "input": 0, "cached": 0, "output": 0, "reasoning": 0,
            "peak": 0, "big_out": 0, "compactions": 0, "usd": 0.0, "models": set()}

def add(acc, c):
    acc["calls"] += 1; acc["input"] += c["input"]; acc["cached"] += c["cached"]
    acc["output"] += c["output"]; acc["reasoning"] += c["reasoning"]
    acc["peak"] = max(acc["peak"], c["input"]); acc["usd"] += call_cost(c); acc["models"].add(c["model"])

def turn_label(ts, txt):
    ev = txt[txt.rfind("<buzz-event"):]
    who = re.search(r"From: (\S+)", ev); what = re.search(r"Content: (.*?)\n", ev)
    when = (ts or "")[5:16].replace("T", " ")
    return f"{when} {who.group(1) if who else '?'}: {(what.group(1) if what else '').strip()}"[:40]

def text_of(content):
    if isinstance(content, str): return content
    return " ".join(x.get("text", "") for x in (content or [])
                    if isinstance(x, dict) and x.get("type") in ("text", "input_text"))

def size_of(o):
    return len(o if isinstance(o, str) else json.dumps(o))

def parse_codex(f):
    sess, turns, cur = blank(), [], None
    for line in open(f, errors="replace"):
        try: d = json.loads(line)
        except ValueError: continue
        t, p = d.get("type"), d.get("payload") or {}
        if not isinstance(p, dict): p = {}
        if t == "compacted":
            for a in (sess, cur):
                if a is not None: a["compactions"] += 1
        elif t == "response_item" and p.get("type") == "message" and p.get("role") == "user":
            txt = text_of(p.get("content"))
            if "<buzz-event" in txt:  # the first turn arrives bundled with the base prompt
                cur = blank(turn_label(d.get("timestamp"), txt)); turns.append(cur)
        elif t == "response_item" and p.get("type") in ("custom_tool_call_output", "function_call_output"):
            for a in (sess, cur):
                if a is not None: a["big_out"] = max(a["big_out"], size_of(p.get("output")) // 4)
        elif t == "event_msg" and p.get("type") == "token_count" and p.get("info"):
            u = p["info"].get("last_token_usage") or {}
            c = {"model": pinned, "input": u.get("input_tokens", 0), "cached": u.get("cached_input_tokens", 0),
                 "write5": u.get("cache_write_input_tokens", 0) or 0, "write1h": 0,
                 "output": u.get("output_tokens", 0), "reasoning": u.get("reasoning_output_tokens", 0)}
            add(sess, c)
            if cur is not None: add(cur, c)
    return os.path.basename(f)[8:24].replace("T", " "), sess, turns

def parse_claude(f):
    # Claude Code writes a response once per content block, each copy carrying the same usage: keep the
    # last copy of each message id, attributed to the turn in which it first appeared.
    sess, turns, cur, first_ts = blank(), [], None, None
    calls, order, turn_of = {}, [], {}
    for line in open(f, errors="replace"):
        try: d = json.loads(line)
        except ValueError: continue
        first_ts = first_ts or d.get("timestamp")
        m = d.get("message") or {}
        if d.get("isCompactSummary") or d.get("type") == "summary":
            for a in (sess, cur):
                if a is not None: a["compactions"] += 1
        if d.get("type") == "user":
            content = m.get("content")
            txt = text_of(content)
            if "<buzz-event" in txt:
                cur = blank(turn_label(d.get("timestamp"), txt)); turns.append(cur)
            if isinstance(content, list):
                for x in content:
                    if isinstance(x, dict) and x.get("type") == "tool_result":
                        for a in (sess, cur):
                            if a is not None: a["big_out"] = max(a["big_out"], size_of(x.get("content")) // 4)
        elif d.get("type") == "assistant" and m.get("model") not in (None, "<synthetic>") and m.get("usage"):
            mid = m.get("id") or d.get("requestId") or d.get("uuid")
            if mid not in calls: order.append(mid); turn_of[mid] = cur
            calls[mid] = m
    for mid in order:
        m = calls[mid]; u = m["usage"]; cc = u.get("cache_creation") or {}
        write = u.get("cache_creation_input_tokens", 0) or 0
        w1h = cc.get("ephemeral_1h_input_tokens", 0) or 0
        c = {"model": m["model"],
             "input": (u.get("input_tokens", 0) or 0) + (u.get("cache_read_input_tokens", 0) or 0) + write,
             "cached": u.get("cache_read_input_tokens", 0) or 0, "write5": write - w1h, "write1h": w1h,
             "output": u.get("output_tokens", 0) or 0,
             "reasoning": (u.get("output_tokens_details") or {}).get("thinking_tokens", 0) or 0,
             "geo": u.get("inference_geo"), "speed": u.get("speed")}
        add(sess, c)
        if turn_of[mid] is not None: add(turn_of[mid], c)
    return (first_ts or "")[:16].replace("T", " "), sess, turns

if harness == "codex-acp":
    pattern, parse = "~/.codex/sessions/*/*/*/rollout-*.jsonl", parse_codex
elif harness == "claude-agent-acp":
    pattern, parse = "~/.claude/projects/*/*.jsonl", parse_claude
else:
    print(f"{role} runs {harness}: not a metered harness this reads (local and subscription roles bill no tokens)")
    sys.exit(0)
files = sorted((f for f in glob.glob(os.path.expanduser(pattern)) if os.path.getmtime(f) >= cutoff),
               key=os.path.getmtime)
if not files:
    print(f"no {harness} sessions for {role} since {since}"); sys.exit(0)

def k(n): return f"{n/1000:,.0f}K" if n >= 1000 else str(n)
def row(a):
    pct = f"{100 * a['cached'] / a['input']:.0f}%" if a["input"] else "-"
    return (f"{a['calls']:>5}  {k(a['input']):>7}  {pct:>4}  {k(a['output']):>6}  {k(a['reasoning']):>6}"
            f"  {k(a['peak']):>6}  {k(a['big_out']):>6}  {a['compactions']:>4}  ${a['usd']:6.2f}")

print(f"{role} — {harness}, manifest model {pinned}" + ("; prices from --usd" if OVERRIDE else "") + "\n")
print(f"{'':42}{'calls':>5}  {'input':>7}  {'cach':>4}  {'output':>6}  {'reason':>6}  {'peak':>6}  {'big':>6}  {'cmpt':>4}  {'est.$':>7}")
print(f"{'':42}{'':>5}  {'tokens':>7}  {'ed':>4}  {'':>6}  {'':>6}  {'ctx':>6}  {'out*':>6}")
total = blank()
for f in files:
    start, sess, turns = parse(f)
    models = ",".join(sorted(sess["models"])) or "no calls"
    label = f"session {start}, {len(turns)} turn{'s' if len(turns) != 1 else ''}"
    print(f"{label:42}{row(sess)}  [{models}]")
    if show_turns:
        for tr in turns: print(f"  {tr['label']:40}{row(tr)}")
    for key in ("calls", "input", "cached", "output", "reasoning", "compactions", "usd"): total[key] += sess[key]
    total["peak"] = max(total["peak"], sess["peak"]); total["big_out"] = max(total["big_out"], sess["big_out"])
    total["models"] |= sess["models"]
print(f"{'total since ' + since:42}{row(total)}")

print("\n* big out: the largest tool output, in tokens (about 4 characters each), re-sent on every later call.")
if not OVERRIDE:
    today = datetime.date.today()
    for m in sorted(total["models"]):
        p = PRICES.get(m)
        if not p: continue
        line = (f"  prices for {m}: ${p['input']:.2f} input, ${p['cached_input']:.2f} cached, "
                f"${p['cache_write']:.2f} cache write, ${p['output']:.2f} output per 1M; "
                f"checked {p.get('checked')} at {p.get('source', '?')}")
        if p.get("promotional_until"): line += f"; promotional until {p['promotional_until']}"
        print(line)
        checked, promo = p.get("checked"), p.get("promotional_until")
        if (checked and (today - checked).days > 45) or (promo and today > promo):
            print(f"  WARNING: the {m} prices are stale — re-check them and update crew/prices.yaml")
if unpriced:
    print(f"  NO PRICE in crew/prices.yaml for: {', '.join(sorted(unpriced))} — those calls count as $0 above")
if total["models"] and pinned not in total["models"]:
    print(f"  NOTE: the manifest says {pinned}, but the API recorded {', '.join(sorted(total['models']))}")
PY
