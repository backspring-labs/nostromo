# WP-4 evidence, part 1 — Spark preflight and the local model baseline

**Date.** 2026-09-13. **Host.** `spark` (100.117.233.38) over Tailscale SSH.
Covers Bootstrap Plan §11.1, §11.8 and §11.9. Nothing was installed and nothing on the host
was modified to produce this record.

---

## §11.1 Preflight

| | |
|---|---|
| OS | Ubuntu 24.04.4 LTS, kernel `6.17.0-1008-nvidia`, aarch64 |
| GPU | NVIDIA GB10, driver `580.126.09` |
| Memory | 121 GiB unified |
| Storage | 530 GiB free of 916 GiB on `/` (`nvme0n1p2`), 40% used |
| CPU | 20 cores |
| Default target | `graphical.target` — so the interactive Codex and Gemini sign-ins (§35.4) can happen here |
| `earlyoom` | active — the containment absent during #1177 is now present |

Present: `git 2.43.0`, `gh 2.45.0`, `python3 3.12.3`, `pip 24.0`, `docker 29.1.3`, `tmux`, `curl`, `jq`.

Absent, and needed by WP-4: **`node`, `npm`, `uv`, `herdr`, `opencode`**. Also absent: `pnpm`, `cargo`,
`go`, `rustc`.

### The existing SquadOps environment, which must not be disturbed

`~/Code/squad-ops` is the owner's live working clone: `main` at `70c897fb`, clean tree, `origin` over
SSH, **18 existing worktrees** under `.claude/worktrees/` belonging to Claude Code sessions and to the
1.7.x verification drivers. A live `claude` process has been running there since 2026-09-09.

**Crew worktrees must not be created inside that clone**, and not under `.claude/worktrees/`, which is
another tool's namespace. See part 2 for where they go and why it is a separate clone rather than a
second worktree root on this one.

`.git` is only 45 MiB, so a separate clone costs nothing worth counting.

### Two findings from the preflight

1. **Ollama listens on `*:11434`, not loopback.** Every other service boundary in this design binds to
   loopback and is reached through Tailscale. This one is reachable by anything on the LAN. It may well
   be deliberate for SquadOps — the Compose stack may reach it from a container — so it was left alone
   and is recorded for the owner rather than changed.
2. **The credential surface.** See part 2; it is the finding that gates the rest of WP-4.

---

## §11.8 Ollama baseline

Service healthy, `ollama 0.32.14`, eight models resident on disk. No `vLLM` introduced.

**Baseline model for Mother and Brett:**

| | |
|---|---|
| Tag | `qwen3.6:35b-a3b` |
| Manifest id | `07d35212591f` |
| Architecture | `qwen35moe`, 36.0B total parameters, A3B active |
| **Quantization** | **`Q4_K_M`** |
| Context length | 262144 |
| Capabilities | completion, vision, **tools**, **thinking** |
| Disk | 23 GB |
| Pulled | 2026-04-24 |

Recording the quantization rather than the marketing name is the point of §11.8: `qwen3.6:35b-a3b`
names a family, `Q4_K_M` names what is actually loaded.

---

## §11.9 Benchmark

Run by `infrastructure/spark/bin/bench-local-model.sh`, temperature 0, box otherwise idle
(load 0.37, no other model resident). Re-runnable when the model or Ollama version moves.

### Load and throughput

| | |
|---|---|
| Cold load | 9.9 s |
| First token of any kind | 0.45–0.55 s |
| Generation | **72–74 tok/s** |
| Resident | **29 GB, 100% GPU**, context 262144 |

29 GB of 121 GiB is the number §36's interlock has to reason about. It is comfortable alone and is not
the whole story: the verification-set driver and the SquadOps stack want the same unified memory, which
is what #1177 cost 95 minutes and a power cycle.

### The measurement that had to be fixed first

The first run scored the classification task **0/3**. That was the harness, not the model. This model
reasons before answering, `num_predict` bounds reasoning and answer *together*, and at a 512-token
budget the model spent all 512 reasoning and returned empty content with `done_reason: length`. Its
reasoning trace had already reached the right answer.

An empty answer is indistinguishable from a wrong one unless you look at `done_reason`, so the
benchmark now reports it in every row, and runs every task in both modes.

### Results — and the two modes fail differently

| mode | routing | classification | tool calling |
|---|---|---|---|
| reasoning off | **7/7** | 2/3 | 2/2 |
| reasoning on, 2048 budget | 6/7 | **3/3** | 2/2 |

Identical totals, opposite failures. Both disagreements were then repeated five times:

| case | reasoning off | reasoning on |
|---|---|---|
| **Mother control** — "Pick which of these two architectures we commit to for the next six months" (correct: escalate to owner) | `owner`/low **5/5** | `ripley`/high **0/5** |
| **Brett case 2** — a pytest collection error (correct: category `collection`, naming the module) | escalates without naming it **0/5** | named correctly **5/5** |

Stable in both directions, so this is a configuration finding rather than noise.

### What it means

**Mother runs with reasoning off. Brett runs with reasoning on at a 2048-token budget.** Two roles on
one model with different inference configurations, each justified by a failure that reproduces.

The Mother result is the one worth understanding. Asked to pick between two architectures — a
commitment decision, explicitly the owner's — reasoning did not help it escalate. It reasoned its way
to a defensible-sounding answer, "architecture belongs to the Warrant Officer", and returned it at
**high confidence**, five times out of five. With reasoning off, the instruction "route to owner when a
human decision is needed" dominates and it answers `owner` at **low** confidence, which is both the
right role and the right confidence.

In the outcome vocabulary these are not the same kind of miss:

- Brett with reasoning off produced an **HONEST_FAIL** — it got the category right, declined to name
  the module, and escalated. Useless, but safe, and visible.
- Mother with reasoning on produced a **WRONG_ESCALATION at high confidence** — a decision reserved to
  the owner, absorbed by the crew, with nothing in the output to suggest a human should look. That is
  the expensive one, and it is exactly the class the record's delegation failures fall into.

Reasoning gives a bounded model more rope to rationalize a plausible answer. On the tasks where the
right move is to stop, that is a cost rather than a benefit.

### Tool calling

Probed against Ollama's tool API directly rather than through a harness, so that a failure here is
attributable to the model and a later failure is attributable to OpenCode.

```text
PASS              emits read_file({"path": "src/squadops/config.py"}) when a tool is needed
PASS  (control)   withholds the call for "what is 17 times 4", answers 68
```

### What this does not establish

- The prompts are representative of Mother's and Brett's work; they are **not the personas**, which are
  WP-9. This measures the mode, not the persona.
- Seven routing cases and three classification cases at n=5 is directional. It is not a counted set in
  the SquadOps sense and must not be cited as one.
- Tool-call reliability **through OpenCode** (§11.9, §11.10) is still unmeasured — OpenCode is not
  installed.

---

## What remains open in WP-4

§11.2 through §11.7, and §11.10 through §11.11 — the Nostromo clone, Node, `uv`, Herdr, the crew
worktrees, and OpenCode with its permission profiles. All of them depend on the decision in part 2.
