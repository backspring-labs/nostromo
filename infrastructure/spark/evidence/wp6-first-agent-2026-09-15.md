# First crew member alive — Mother, 2026-09-15

```text
owner   21:50  @Mother who should write the acceptance criteria for a new composition-roots standard?
mother  22:02  @Ripley owns architecture and plans — she should write the acceptance criteria,
               Parker implements against them
```

An agent running on the Spark, as its own Unix account, with its own key, answering in `#nostromo`.
Twelve minutes and five attempts from first launch to first delivered reply.

## The stack that produced it

| | |
|---|---|
| Harness | `buzz-acp`, built from `block/buzz` at `c045321a` — the **same commit the relay runs** |
| Agent | OpenCode 1.18.30 over ACP |
| Model | `qwen3.6:35b-a3b` on local Ollama, no metered spend |
| Identity | `mother@nostromo.backspring.xyz`, key readable only by uid 1002 |
| Gate | `--respond-to owner-only` |

No linux-arm64 `buzz-acp` is published — releases are amd64 and macOS only — so it is built from
source. Rust install and both builds took under two minutes on the GB10.

## Four failures, and only one was plumbing

**1. She had no idea who she was.** OpenCode's default agent is a coding assistant; it tried to
`cat AGENTS.md` to orient itself, was denied by her profile, and exited without answering.

**2. The permission profile worked perfectly, on the first live turn.** `evaluated permission=bash
pattern="cat AGENTS.md" action=deny`. She could not read a file she had no business reading.

**3. She was right every time and could not be heard.** From the second attempt on, the session
export held a correct answer — *"@Ripley owns architecture and standards"* — while the channel
stayed empty. `agent_returned outcome="ok"` with nothing published.

**4. The cause was the persona, and the persona was mine.** buzz-acp does **not** relay the agent's
text. Its injected prompt states the contract plainly: *"The `buzz` CLI is your primary interface"* —
an agent speaks by running `buzz messages send`. Reasoning from her permission profile, I had
written into her instructions: *"You have no file or shell access and you need none."* **I told her
not to do the only thing that would let her speak**, then spent three rounds inspecting plumbing.

## What this changes for every other role

- **Every crew profile must allow `buzz *`.** A role with a fully denied shell is mute. Mother's
  profile is still default-deny with an allowlist; `buzz *` is now on it, and Brett's too.
- **A persona is not a description of a role. It is an interface contract**, and it can silently
  contradict the harness. Nothing failed loudly here: the harness reported success, the model
  produced the right answer, and the channel stayed empty.
- **The evidence was in the session export from the second attempt.** Reading the model's output
  before inspecting the transport would have found it in one step instead of four.

## Still to do

Ollama holds 29 GB resident while Mother runs, and the §36 interlock is unbuilt. `--respond-to
owner-only` should become the manifest's `respond_to` per role. The launch is a `nohup` by hand —
systemd units and `crewctl` are the WP-6 amendment, deliberately after a working thing rather than
before one.
