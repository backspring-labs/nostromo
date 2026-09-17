# Buzz, Herdr and tmux — what each is actually for

Written 2026-09-17, after two days of bringing up Mother and Brett, and prompted by a question
worth recording: *what does Herdr offer over tmux, and how does either compare to Buzz?*

The short answer is that the question contains a category error, and seeing why is the useful part.

---

## Three tools, three layers

| tool | describes itself as | the problem it set out to solve |
|---|---|---|
| **tmux** (2007) | terminal multiplexer | keep a terminal alive across a disconnect; split one terminal into many |
| **Herdr** (0.9.0) | *"terminal workspace manager for AI coding agents"* | tmux's problem restated for one human orchestrating several agent sessions |
| **Buzz** | *"a Nostr-based messaging platform for human-agent collaboration"* | make agents addressable members of a durable, multi-party conversation |

They are not competitors. They occupy different layers and compose:

```
Buzz        how agents are addressed, remember, and leave a record     ← identity / communication
systemd     how agents exist                                           ← supervision
Herdr/tmux  how the owner watches and drives                           ← ergonomics
```

Running Herdr on the Spark to attach to Brett's worktree, while `nostromo@brett` serves the channel
under systemd, is all three at once with nothing in conflict.

---

## Comparison, scored against each tool's own intent

`—` means *not attempting this*, which is different from failing at it.

| | Buzz | Herdr | tmux |
|---|---|---|---|
| Addressable identity | ✅ its whole point | — | — |
| Durable signed record | ✅ | — | — |
| Presence / peer discovery | ✅ | — | — |
| Cross-session memory | ✅ | — | — |
| Multi-human | ✅ | ❌ | ❌ |
| Agent process management | — (systemd's) | ✅ | — |
| Git worktree helpers | — | ✅ | — you script it |
| Remote machine profiles | — | ✅ | — you script it |
| Many panes, one screen | — | ✅ + layouts | ✅ |
| Session survives disconnect | — not attempting | ✅ | ✅ its whole point |
| Survives reboot | — (systemd's) | ❌ | ❌ |

Read down the columns: Buzz is dense at the top, the multiplexers at the bottom, and the middle
band is Herdr's alone. **The only row where two columns genuinely contend is agent process
management — and that is Herdr against systemd, not against Buzz.**

---

## The same agent, in each mode

More concretely: what does Brett have, depending on how he is running?

| | Buzz community member | Herdr session | tmux session |
|---|---|---|---|
| Runs as | brett's uid | brett's uid | brett's uid |
| Started by | systemd, at boot | you | you |
| Initiated by | an `@mention` arriving | you typing | you typing |
| Survives reboot | ✅ `enabled` | ❌ | ❌ |
| Survives crash | ✅ `Restart=always` | ❌ | ❌ |
| Community identity | ✅ signing key in env | ❌ | ❌ |
| Addressable by members | ✅ | ❌ | ❌ |
| Can address members | ✅ | ❌ | ❌ |
| Peer-aware — roster, presence, siblings | ✅ | ❌ | ❌ |
| Core memory | ✅ encrypted, survives restarts | ❌ | ❌ |
| Team instructions injected | ✅ `<team-instructions>` | only if pasted | only if pasted |
| Delivery contract | text discarded — must publish | text *is* the answer | text *is* the answer |
| Harness | `buzz-agent` (no TUI) | Goose / OpenCode | Goose / OpenCode |
| Filesystem boundary | uid + mode bits | **identical** | **identical** |
| GitHub App | mint on demand | **identical** | **identical** |
| Commit attribution | `nostromo-brett[bot]` | **identical** | **identical** |
| Output durable | signed events + journald | scrollback | scrollback |
| Logs the agent cannot delete | ✅ journald | ❌ | ❌ |

### Three things this exposes

**The first column is three layers, not one.** Buzz supplies identity, addressability, peers,
memory and the publish contract. systemd supplies existence. The OS and GitHub supply the
boundaries. Conflating them is how "Herdr supervises the crew" survived as long as it did.

**An agent can move between modes without losing what constrains it.** Same uid, same clone, same
bot identity, same path boundaries. What it loses is exactly the Buzz layer: it cannot be
addressed, cannot answer anyone, and does not remember.

**Commit attribution is identical in all three, and that is a real gap.** The GitHub record says
`nostromo-brett[bot]` whether the agent acted autonomously or the owner drove the account by hand.
Nothing distinguishes them. This is inherent — the owner has sudo and can always become a role —
but the operating model leans on a distinction the record does not make. If it ever matters, the
cheap fix is a marker: bench sessions push to `nostromo/<role>/bench/*`, or carry a commit trailer.

---

## Why Herdr is not the supervisor

Recorded because it was decided once and should not need deciding again (WP-6 amendment).

An agent's durability lives in a set of durable facts — a key in a 600 file, a uid, a row in the
relay's member table, a definition in git. Every one survives a reboot, a crash, a closed laptop
and a harness swap. **Binding an agent's existence to a terminal session binds it to the most
ephemeral layer in the stack.**

The costs were concrete: a crashed Herdr server takes every agent with it, a closed session deletes
one, nothing returns after a reboot, and a harness that panics stays dead until somebody notices.

The division that replaced it:

| | owns | why |
|---|---|---|
| **systemd** | existence | restart on failure, start on boot, `MemoryMax`, journald |
| **Buzz** | identity and voice | who it is, what it says, how it is addressed |
| **Herdr** | observation | attaching to look, or working by hand as a role |

Proven rather than asserted, 2026-09-16: `systemctl kill -s KILL nostromo@mother` → new MainPID
ten seconds later, same identity, re-attested, re-subscribed, answering in the channel. The agent
survived the destruction of its own process.

**And under `buzz-agent` there is nothing to watch anyway.** It is a stdio JSON-RPC server with no
TUI, as is every harness in the manifest — `codex-acp`, `claude-agent-acp`, `gemini-acp`. A pane
pointed at a crew member shows ACP frames scrolling past. The output surface is the channel; the
diagnostics are `journalctl -u nostromo@<role>`.

---

## What Herdr is still for

Two things, both genuinely useful, neither load-bearing:

**A persistent shell as a role, in that role's checkout.** `ssh spark` plus `sudo -iu brett` gets
you there already; Herdr adds a session that survives closing your laptop mid-investigation. That
is real value when you are reproducing something a role reported.

**A bench.** Talking to a role's persona and model directly, with no Buzz — no key, no channel, no
identity collision — to evaluate the configuration itself. Every choice made in this system so far
(buzz-agent over Goose, dense 27b over the MoE, 60 rounds, the trimmed base prompt) was decided on
one or two observations. A bench makes the next round measurable.

Note what a bench can and cannot tell you. It isolates cleanly to *is the persona any good, and is
the model good enough* — because a direct session has to use a different harness, `buzz-agent`
having no interactive mode. It tells you nothing about the stack, because every expensive failure
so far has been a **seam**: text discarded by the harness, rounds capped silently, backgrounded
work reaped by an ephemeral shell, a memory write refused for want of an owner attestation. None of
those exist in a terminal session.

**Taking the seat.** One identity, one process. A hand-run harness holding a role's key while its
unit is active means two processes answering the same mention, signed identically, with no way to
tell which said what. The adapter's single-instance guard catches the sanctioned path; a hand-run
harness bypasses it. So:

```
systemctl stop nostromo@brett     # the unit releases the identity
…work as brett…                   # Herdr's persistence earns its keep here
systemctl start nostromo@brett    # hand it back
```

`Restart=always` does not fight an explicit `stop`.

---

## Others worth considering

**GitHub itself** — the serious contender, and the one to think hardest about. It already has a
durable record, bot identities via Apps, attribution, review gates, notifications and threaded
discussion. The crew constitution already splits them: *"GitHub artifact is the record. Buzz Canvas
or thread is the workbench."* Buzz adds synchronous, ad-hoc, not-repo-shaped conversation with
presence and memory; GitHub adds being where the work already lives. Worth being explicit that both
are running deliberately.

**Matrix** — the closest architectural analog to Buzz: federated, durable, bot-friendly, mature.
No agent-memory primitive and no NIP-OA-style ownership attestation, and a homeserver replaces the
relay.

**Zellij** — tmux's modern rival, with layouts as config and a WASM plugin system. If Herdr's value
is "tmux plus agent workflow", Zellij is "tmux plus the API you would build that on".

**Claude Squad, conductor, container-use** — a crop of run-N-agents-in-parallel-worktrees tools
overlapping Herdr directly. Worth a look to confirm Herdr is the best of them for this case.

**Temporal** — if durability of *work* rather than of *conversation* ever becomes the pain, none of
the above covers that layer.
