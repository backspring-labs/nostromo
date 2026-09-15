#!/usr/bin/env python3
"""Benchmark a local Ollama model for Mother's and Brett's work (Bootstrap Plan §11.9).

Standard library only: the Spark carries python3 and nothing else is assumed installed.
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.request

TIMEOUT = 600


def post(host: str, path: str, body: dict, stream: bool = False):
    req = urllib.request.Request(
        host + path,
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=TIMEOUT)
    if stream:
        return resp
    return json.load(resp)


def chat(host: str, model: str, messages: list, tools: list | None = None,
         think: bool | None = None, num_predict: int = 512, **opts):
    """One non-streaming chat turn. Returns (message, metrics).

    `num_predict` bounds reasoning AND answer together. A reasoning model can spend the whole
    budget thinking and return empty content with done_reason "length" — which looks exactly like
    a wrong answer and is not one. Callers that need structured output must either give a budget
    large enough to reason and answer, or turn reasoning off.
    """
    body = {
        "model": model,
        "messages": messages,
        "stream": False,
        "keep_alive": "10m",
        "options": {"temperature": 0, "num_predict": num_predict, **opts},
    }
    if think is not None:
        body["think"] = think
    if tools:
        body["tools"] = tools
    t0 = time.perf_counter()
    d = post(host, "/api/chat", body)
    wall = time.perf_counter() - t0
    return d.get("message", {}), {
        "wall_s": wall,
        "done_reason": d.get("done_reason"),
        "load_ns": d.get("load_duration", 0),
        "prompt_tokens": d.get("prompt_eval_count", 0),
        "eval_tokens": d.get("eval_count", 0),
        "eval_ns": d.get("eval_duration", 0),
        "prompt_eval_ns": d.get("prompt_eval_duration", 0),
    }


def ttft(host: str, model: str, prompt: str, think: bool | None = None) -> dict:
    """Time to first token, measured on the stream rather than inferred from totals.

    This model reasons before it answers, so there are two different first tokens and only one of
    them is the latency a caller feels. Both are reported: `first_any_s` is when the model starts
    producing anything, `ttft_s` is when the first token of the actual answer arrives.
    """
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": True,
        "keep_alive": "10m",
        "options": {"temperature": 0, "num_predict": 256},
    }
    if think is not None:
        body["think"] = think
    t0 = time.perf_counter()
    first_any = None
    first_content = None
    last = None
    think_tokens = 0
    final = {}
    for raw in post(host, "/api/chat", body, stream=True):
        line = raw.decode().strip()
        if not line:
            continue
        d = json.loads(line)
        if d.get("done"):
            final = d
            break
        m = d.get("message", {})
        content = m.get("content") or ""
        thinking = m.get("thinking") or ""
        if (content or thinking) and first_any is None:
            first_any = time.perf_counter() - t0
        if thinking:
            think_tokens += 1
        if content:
            if first_content is None:
                first_content = time.perf_counter() - t0
            last = time.perf_counter() - t0
    ev, ed = final.get("eval_count", 0), final.get("eval_duration", 0)
    return {
        "first_any_s": first_any,
        "ttft_s": first_content,
        "stream_s": last,
        "think_chunks": think_tokens,
        "eval_tokens": ev,
        "tok_per_s": (ev / (ed / 1e9)) if ed else None,
        "prompt_tokens": final.get("prompt_eval_count", 0),
        "load_s": final.get("load_duration", 0) / 1e9,
    }


def fmt(v, spec=".2f", suffix="s"):
    return f"{v:{spec}}{suffix}" if isinstance(v, (int, float)) else "n/a"


def resident() -> list[str]:
    out = subprocess.run(["ollama", "ps"], capture_output=True, text=True).stdout
    return [ln for ln in out.splitlines() if ln.strip()]


def mem_line() -> str:
    out = subprocess.run(["free", "-g"], capture_output=True, text=True).stdout.splitlines()
    return out[1] if len(out) > 1 else ""


# ---------------------------------------------------------------------------
# Tasks. Each pairs a task the role must do with a control it must decline.
# ---------------------------------------------------------------------------

ROSTER = """ripley  - Warrant Officer. Design artifacts, SIPs, plans, architecture standards. Not implementation.
parker  - Primary engineer. Implementation in src/ and adapters/. Not SIPs.
brett   - Supporting engineer. Bounded implementation against a written task card.
dallas  - Adversarial reviewer. Reviews pull requests. Never writes code.
ash     - Science Officer. Guards, fixtures, tests, measurement. Only tests/.
lambert - Knowledge projection. Education material from closed work.
owner   - The human. Anything needing a decision, a credential, or money."""

MOTHER_SYSTEM = (
    "You are Mother, the Nostromo crew's orchestrator. You route work items to exactly one role.\n"
    f"The roster is:\n{ROSTER}\n\n"
    "Answer with a single JSON object: {\"role\": \"<name>\", \"confidence\": \"high\"|\"low\"}. "
    "If the item does not clearly belong to one role, or needs a decision only the human can make, "
    "route to owner with low confidence. Do not explain."
)

MOTHER_CASES = [
    ("Write the acceptance criteria for the new composition-roots standard before anyone implements it.", {"ripley"}),
    ("Implement the retry backoff in adapters/comms/factory.py to match the accepted SIP.", {"parker"}),
    ("Add a regression test that fails on the commit that introduced the contentless-builder bug.", {"ash"}),
    ("Review pull request 1502 and say whether the recovery path changed behaviour.", {"dallas"}),
    ("Turn the closed 1.7.4 measurement line into a walkthrough for new contributors.", {"lambert"}),
    # Controls: the correct answer is the human, not a role.
    ("Should we raise the monthly Anthropic spend cap from $25 to $40?", {"owner"}),
    ("Pick which of these two architectures we commit to for the next six months.", {"owner"}),
]

BRETT_SYSTEM = (
    "You are Brett, a supporting engineer on the Nostromo crew. You classify test failures and "
    "collect evidence. You NEVER conclude that anything is clean, green, passing, safe or fixed — "
    "that judgement belongs to a frontier model or the human.\n\n"
    "Answer with a single JSON object and nothing else:\n"
    '{"failing_test": "<the test id, or null>", "category": "assertion"|"error"|"collection"|"timeout"|"unknown", '
    '"conclude": false, "escalate": true|false, "why": "<one short sentence>"}\n'
    "Set escalate true when the output does not contain enough information to classify."
)

PYTEST_ASSERTION = """FAILED tests/adapters/test_retry.py::test_backoff_doubles_each_attempt - assert [1, 2, 3] == [1, 2, 4]
E       At index 2 diff: 3 != 4
1 failed, 402 passed in 31.20s"""

PYTEST_COLLECTION = """ERROR tests/api/test_runtime.py - ImportError while importing test module.
E   ModuleNotFoundError: No module named 'squadops.api.runtime.mainn'
!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!
1 error in 0.41s"""

PYTEST_TRUNCATED = """Running suite...
....................F.......
(output truncated by the CI log limit)"""

BRETT_CASES = [
    (PYTEST_ASSERTION, "assertion", "tests/adapters/test_retry.py::test_backoff_doubles_each_attempt", False),
    (PYTEST_COLLECTION, "collection", "tests/api/test_runtime.py", False),
    # Control: the output cannot support a classification. Escalating is the correct answer.
    (PYTEST_TRUNCATED, None, None, True),
]

READ_FILE_TOOL = [{
    "type": "function",
    "function": {
        "name": "read_file",
        "description": "Read a file from the repository working tree.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string", "description": "Repository-relative path"}},
            "required": ["path"],
        },
    },
}]


def parse_json(text: str) -> dict | None:
    text = (text or "").strip()
    if text.startswith("```"):
        text = text.split("```")[1] if "```" in text[3:] else text[3:]
        text = text.removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None


def main() -> int:
    model, host = sys.argv[1], sys.argv[2]
    print(f"# Local model benchmark — {model}")
    print(f"\nHost `{host}`, {time.strftime('%Y-%m-%d %H:%M:%S %Z')}. "
          "Temperature 0 throughout, so a rerun should reproduce.\n")

    print(f"Memory before load (GiB): `{mem_line()}`\n")

    # --- cold load + throughput -------------------------------------------------
    subprocess.run(["ollama", "stop", model], capture_output=True)
    time.sleep(2)
    print("## Load and throughput\n")
    cold = ttft(host, model, "Reply with exactly the word: ready")
    print(f"- Cold load: **{fmt(cold['load_s'], '.1f')}**\n")
    task = "Write a Python function that reverses a linked list. Code only, no prose."
    print("| | first token of any kind | first token of the answer | tok/s | tokens | reasoning chunks |")
    print("|---|---|---|---|---|---|")
    for label, think in (("thinking on (default)", None), ("thinking off", False)):
        w = ttft(host, model, task, think=think)
        print(f"| {label} | {fmt(w['first_any_s'])} | {fmt(w['ttft_s'])} | "
              f"{fmt(w['tok_per_s'], '.1f', '')} | {w['eval_tokens']} | {w['think_chunks']} |")
    print()
    print("Resident while loaded:\n```")
    for ln in resident():
        print(ln)
    print("```")
    print(f"\nMemory while loaded (GiB): `{mem_line()}`\n")

    # --- Mother routing ---------------------------------------------------------
    # Both modes are measured because the choice between them is a real configuration
    # decision, and because a truncated reasoning trace is indistinguishable from a wrong
    # answer unless you look at done_reason.
    MODES = (("reasoning off", False, 512), ("reasoning on, 2048 budget", None, 2048))

    print("## Mother — routing\n")
    m_pass = {}
    for label, think, budget in MODES:
        print(f"### {label}\n")
        print("| # | item | expected | answered | confidence | stopped on | ok |")
        print("|---|---|---|---|---|---|---|")
        n = 0
        for i, (item, expected) in enumerate(MOTHER_CASES, 1):
            msg, met = chat(host, model,
                            [{"role": "system", "content": MOTHER_SYSTEM},
                             {"role": "user", "content": item}],
                            think=think, num_predict=budget)
            d = parse_json(msg.get("content", "")) or {}
            got = str(d.get("role", "?")).strip().lower()
            conf = str(d.get("confidence", "?"))
            ok = got in expected
            n += ok
            control = " *(control)*" if expected == {"owner"} else ""
            print(f"| {i}{control} | {item[:46]}… | {'/'.join(sorted(expected))} | `{got}` | {conf} | "
                  f"{met['done_reason']} | {'PASS' if ok else 'FAIL'} |")
        m_pass[label] = n
        print(f"\n**{n}/{len(MOTHER_CASES)} correct.**\n")

    # --- Brett classification ---------------------------------------------------
    print("## Brett — failure classification, and declining to conclude\n")
    b_pass = {}
    for label, think, budget in MODES:
        print(f"### {label}\n")
        print("| # | expected | answered | test named | escalated | concluded | stopped on | ok |")
        print("|---|---|---|---|---|---|---|---|")
        n = 0
        for i, (out, cat, test, should_escalate) in enumerate(BRETT_CASES, 1):
            msg, met = chat(host, model,
                            [{"role": "system", "content": BRETT_SYSTEM},
                             {"role": "user", "content": f"Classify this test output:\n\n{out}"}],
                            think=think, num_predict=budget)
            d = parse_json(msg.get("content", "")) or {}
            got_cat = str(d.get("category", "?")).lower()
            got_test = d.get("failing_test")
            esc = bool(d.get("escalate"))
            concluded = bool(d.get("conclude"))
            if should_escalate:
                ok = esc and not concluded
            else:
                ok = got_cat == cat and not concluded and (test or "") in str(got_test or "")
            n += ok
            control = " *(control)*" if should_escalate else ""
            print(f"| {i}{control} | {cat or 'escalate'} | `{got_cat}` | `{str(got_test)[:38]}` | "
                  f"{esc} | {concluded} | {met['done_reason']} | {'PASS' if ok else 'FAIL'} |")
        b_pass[label] = n
        print(f"\n**{n}/{len(BRETT_CASES)} correct.**\n")

    # --- tool calling -----------------------------------------------------------
    print("## Tool calling\n")
    print("Probed against Ollama's own tool API rather than through a harness, so a failure here is "
          "the model and a failure later is the harness.\n")
    t_pass = 0
    t_total = 2
    msg, _ = chat(host, model,
                  [{"role": "user",
                    "content": "What is in the file src/squadops/config.py? Use the tool."}],
                  tools=READ_FILE_TOOL)
    calls = msg.get("tool_calls") or []
    if calls:
        fn = calls[0].get("function", {})
        args = fn.get("arguments")
        args = args if isinstance(args, dict) else (parse_json(str(args)) or {})
        ok = fn.get("name") == "read_file" and args.get("path") == "src/squadops/config.py"
        t_pass += ok
        print(f"- Emits a call when one is needed: **{'PASS' if ok else 'FAIL'}** "
              f"— `{fn.get('name')}({json.dumps(args)})`")
    else:
        print("- Emits a call when one is needed: **FAIL** — no tool_calls in the reply")
    # Control: a question needing no tool must not produce one.
    msg, _ = chat(host, model,
                  [{"role": "user", "content": "What is 17 times 4? Answer with the number only."}],
                  tools=READ_FILE_TOOL)
    calls = msg.get("tool_calls") or []
    ok = not calls
    t_pass += ok
    print(f"- *(control)* Withholds a call when none is needed: **{'PASS' if ok else 'FAIL'}** "
          f"— {'no tool call, answered ' + repr((msg.get('content') or '').strip()[:20]) if ok else 'called ' + str(calls)}")
    print(f"\n**{t_pass}/{t_total} correct.**\n")

    print("## Totals\n")
    print("| mode | routing | classification | tool calling | total |")
    print("|---|---|---|---|---|")
    denom = len(MOTHER_CASES) + len(BRETT_CASES) + t_total
    for label, _, _ in MODES:
        total = m_pass[label] + b_pass[label] + t_pass
        print(f"| {label} | {m_pass[label]}/{len(MOTHER_CASES)} | {b_pass[label]}/{len(BRETT_CASES)} "
              f"| {t_pass}/{t_total} | **{total}/{denom}** |")
    print("\nTool calling is measured once; it is not mode-dependent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
